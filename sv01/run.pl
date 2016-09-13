#!/usr/bin/perl
use Data::Dumper;
use Carp;
use Time::HiRes qw(time sleep);
use Getopt::Long;
use IO::Select;
use Fcntl;
use File::Slurp;
use lib "../dockerpipes";
use DockerPipes;

$usage = <<EOS;
$0 cmd options
	valid commands:
		container containername videoserverport 
			--appname 

		start containername port 
			reads input from DockerPipes->{inpipe_jpg}
				limited only by input frame rate and server processing rate

		start2 containername fps port
			reads input from DockerPipes->{inpipe2_jpg} at fps
				produces status messages as appropriate pipe underflow, overflow, etc... 
			options:
				--nooverlay
					no overlay... just passes input to output

		test01 
			two video servers sv01 and sv01 at 5020 and 5021
		test02
			working on inpipe 
		t1,t2,t3,t4
			perl pipe test commands
		exec containername cmd args... 
		inpipe
			activate input pipe... must already exist
	options:
EOS

GetOptions(
	'stringparam=s' => \$options{stringparam},
	'booleanparam' => \$options{booleanparam},
	'appname=s' => \$options{appname},
	'nooverlay' => \$options{nooverlay},
	);


confess $usage
	if !@ARGV;

$command = shift;


if($command eq 'start')
{
	$containername = shift;
	$port = shift;

	confess $usage
		if !$containername || !$port;

	print `./run.pl container $containername $port`;
	print `./run.pl exec $containername startpipe`;
}


elsif($command eq 'start2')
{
       	$containername = shift;
	$fps = shift;
	$port = shift;
	confess $usage
		if !($containername && $fps && $port);
	 print `./run.pl start $containername $port`;
	$dp = DockerPipes->load($containername);
	$dp->{fps} = $fps;
	$dp->{nooverlay} = $options{nooverlay};
	$dp->writeConfig();
	print `./run.pl exec $containername startpipe2`;
}


elsif($command eq 'startpipe2')
{
	$dp = DockerPipes->load(shift);
	confess $usage
		if !$dp;

	$dp->{inpipe2_jpg} = $dp->{myshare} . '/inpipe2.jpg';
	$dp->writeConfig();

	`rm -f $dp->{inpipe2_jpg}`;
	$inframe = 0;

	$i = 1;
	$dp->{fps} = 10
		if !$dp->{fps};

	$period = 1.0/$dp->{fps};
    print $period;

	$dp->{output} = $dp->{myshare} . "/output.jpg";
	$dp->{output2} = $dp->{myshare} . "/output2.jpg";
	print "output: $dp->{output} \n";
	`mkfifo -m 666 $dp->{inpipe_jpg}`;
	print "created input pipe $dp->{inpipe_jpg}\n";
	while(1)
	{
		$t1 = time;
		$infps = 0;
		$infps = $inframe / (time - $inframestarttime) 
			if $inframestarttime;

		$overlaytime = sprintf("fps in: %02.2f  overlay:%02.2f", $infps, 1 / $duration_avg)
			if $duration_avg;

		if(-e $dp->{inpipe2_jpg})
		{
			$status = "pipe exists";
			if(! -e $inpipe)
			{
				sysopen($inpipe, $dp->{inpipe2_jpg}, O_NONBLOCK | O_RDONLY);
				binmode $inpipe;
				$ioselect = IO::Select->new($inpipe);
			}
			@ready = $ioselect->can_read(.001);
			if(@ready)
			{
				$status .= ":can_read";
				$filedatasize = sysread($inpipe, $filedata, 10000000);
				$filedatasize_ = sysread($inpipe, $filedata_, 10000000)
					while $filedatasize && $filedatasize_ && ($filedatasize += $filedatasize_) && ($filedata .= $filedata_);
				
				$totalbytesread += $filedatasize;
				$status = sprintf("bytes read %2.3e",$totalbytesread);
				#close($inpipe);
				if($filedatasize)
				{
					#write_file($dp->{output}, $filedata);
					open $inputjpg, ">$dp->{output}";
					my $ofh = select $inputjpg;
					$| = 1;
					select $ofh;
					syswrite($inputjpg,$filedata);
					close $inputjpg;
					$inframestarttime = time
						if !$inframe;
					$inframe++;
				}
			}
		}
		else
		{
			$status = "no pipe";
			`cp Wait01.jpg $dp->{output}`;
		}

		$framemsg = sprintf("frame in:%d gen:%d",$inframe,$i );
		$timestamp = `date`;
#$cmd =<<EOS;
#convert $dp->{output} \\
#    -resize 800x450\! \\
#    -strip \\
#    -sampling-factor '4:2:2' \\
#    -type TrueColor \\
#    -gravity SouthEast -weight 700 -pointsize 20 -fill red -annotate 0 '$framemsg'  \\
#    $dp->{output2}
#EOS
    # -gravity NorthEast -weight 700 -pointsize 20 -fill red -annotate 0 '$timestamp'  \\
	# -gravity SouthEast -weight 700 -pointsize 20 -fill red -annotate 0 '$framemsg'  \\
	# -gravity SouthWest -weight 700 -pointsize 20 -fill red -annotate 0 '$overlaytime'  \\
	# -gravity NorthWest -weight 700 -pointsize 20 -fill red -annotate 0 '$status'  \\
		if($dp->{nooverlay})
		{
			`cp $dp->{output} $dp->{output2}`;
		}
		else
		{
#			`$cmd`;
            `cp $dp->{output} $dp->{output2}`;
		}
		`cat $dp->{output2} > $dp->{inpipe_jpg}`; #TODO get rid of this debug step
		$t2 = time;
		$duration = $t2 - $t1;
		$duration_total += $duration;
		$duration_avg = $duration_total / $i;
		$sleeptime = $period - $duration;
		$sleeptime = 0
			if $sleeptime < 0;
		#sleep($sleeptime);
        #print $duration;
		++$i;
	}
}


elsif($command eq 'startpipe')
{
	$dp = DockerPipes->load(shift);
	confess $usage
		if !$dp;

	$cmd=<<EOS;
ffmpeg -r 16 -threads 2 -f image2pipe -vcodec mjpeg -i - -r 16 -s 800x450 -vcodec mjpeg -g 1 http://localhost:5001/feed1.ffm > /tmp/startpipe.log 2>&1
EOS
	open $outpipe, "| $cmd";

	$inpipename = $dp->{inpipe_jpg};

	`rm $inpipename`
		if -e $inpipename;

	while(1)
	{
		if(! -e $inpipename)
		{
			print "waiting for pipe: $inpipename to exist\n";
			sleep(1);
			next;
		}
		$filedata = `cat $inpipename`;
		#$filedata = `cat WaitForPipe.jpg`;
		print $outpipe $filedata;
		sleep(.001);
	}

	#wait for inpipe
	$filedata = `cat WaitForPipe.jpg`;
	print $outpipe $filedata;
	while(! -e $inpipename)
	{
		print $outpipe $filedata;
		sleep(.5);
	}

	$filedata = `cat Wait01.jpg`;
	for($i = 0; $i < 3; ++$i)
	{
		print $outpipe $filedata;
		sleep(.5);
	}

	while(1)
	{
		$filedata = `cat $inpipename`;
		#$filedata = `cat WaitForPipe.jpg`;
		print $outpipe $filedata;
		sleep(.1);
	}
}


elsif($command eq 'container')
{
	$c = DockerPipes->create(shift);
	$c->{videoserverport} = shift;

	confess $usage
		if !$c->{containername} || !$c->{videoserverport};

	`docker rm -f $c->{containername}`;

	$cmd =<<EOS;
docker run -d -v \$(pwd):/root/sv01 -v \$(pwd)/../dockerpipes:/root/dockerpipes -v $c->{share_basedir}:$c->{share_basedir} -w /root/sv01 -p $c->{videoserverport}:5001 --name $c->{containername} hmlatapie/gstreamer /bin/bash -c "while true; do date; sleep 3600; done"
EOS

	print `$cmd`;
	print `docker exec -d $c->{containername} /bin/bash -c "./run_ffserver"`;
#	print `docker exec -d $c{containername} /bin/bash -c "while true; do ./run.pl t1 ; done"`;

	$c->{inpipe_jpg} = $c->{myshare} . '/inpipe.jpg'; 
	`rm -f $c->{inpipe_jpg}`;
	$c->writeConfig();
}


elsif($command eq 'exec')
{
	$containername = shift;
	$cmd = shift;
	confess $usage
		if !$containername || !$cmd;
	`docker exec -d $containername /bin/bash -c "while true; do ./run.pl $cmd $containername ; done"`;
}

else
{
	confess $usage;
}


