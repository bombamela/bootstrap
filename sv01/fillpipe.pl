#!/usr/bin/perl
use Data::Dumper;
use Carp;
use Time::HiRes qw(time sleep);
use Getopt::Long;
use lib "../dockerpipes";
use DockerPipes;

$usage = <<EOS;
$0 cmd options
	valid commands:
		doit containername fps
			uses TGX02 data

		doit2 containername fps
			dynamically generates data

		doit3 containername fps
			generates 1000 frames in /tmp/jpgs
			
		doit4 containername 
			uses doit3 to determing maximum frame rate

		convert1
			test imagemagick performance

	options:
		--inpipe2
			writes to inpipe2_jpg instead of inpipe_jpg
EOS

GetOptions(
	'stringparam=s' => \$options{stringparam},
	'booleanparam' => \$options{booleanparam},
	'inpipe2' => \$options{inpipe2}
	);

confess $usage
	if !@ARGV;

$command = shift;

if($command eq 'doit')
{
	my $containername = shift;
	$p = DockerPipes->load($containername);
	confess "containername: $containername doesn't exist"
		if !$p;

	$fps = shift;
	confess $usage
		if !$fps ;

	$outpipe = $p->{inpipe_jpg};
	$outpipe = $p->{inpipe2_jpg}
		if $options{inpipe2};

	`mkfifo -m 666 $outpipe`
		if ! -e $outpipe;
	$jpegdir = "$ENV{HOME}/workdir/jpgs";
	confess "jpeg directory: $jpegdir doesn't exist"
		if ! -d $jpegdir;

	@files = glob("$jpegdir/*.jpg");
	for $file (@files)
	{
		print "sending $file to $outpipe\n";
		`cat $file > $outpipe`;
		sleep(1.0/$fps);
	}
}
elsif($command eq 'doit2')
{
	my $containername = shift;
	$p = DockerPipes->load($containername);
	confess "containername: $containername doesn't exist"
		if !$p;

	$fps = shift;
	confess $usage
		if !$fps;

	$tmpfile = $p->{myshare} . "/tmpfile.jpg";

	$outpipe = $p->{inpipe_jpg};
	$outpipe = $p->{inpipe2_jpg}
		if $options{inpipe2};

	`mkfifo -m 666 $outpipe`
		if ! -e $outpipe;

	$i = 0;
	while(1)	
	{
		print "processing cmd: $cmd\n"
			if ($i % 20) == 0;
		$txt = sprintf("hello world # %05d",$i++);
		$timestamp = `date`;
	$cmd =<<EOS;
convert -size 640x480 xc:white \\
	-gravity center -weight 700 -pointsize 20 -annotate 0 "$txt" \\
	-gravity NorthEast -weight 700 -pointsize 20 -annotate 0 " \n$timestamp" \\
	$tmpfile	
EOS
		`$cmd`;
		`cat $tmpfile > $outpipe`;
		sleep(1/$fps);
	}
}
elsif($command eq 'doit3')
{
	my $containername = shift;
	$p = DockerPipes->load($containername);
	confess "containername: $containername doesn't exist"
		if !$p;

	$fps = shift;
	confess $usage
		if !$fps;

	$outpipe = $p->{inpipe_jpg};
	$outpipe = $p->{inpipe2_jpg}
		if $options{inpipe2};

	`mkfifo -m 666 $outpipe`
		if ! -e $outpipe;

	if(! -d '/tmp/jpgs')
	{
		`mkdir -p /tmp/jpgs`;
		chdir '/tmp/jpgs';
		$i = 1;
		for(;$i<=1000;)
		{
			$txt = sprintf("hello world # %05d",$i);
			$filename = sprintf("testimage%05d.jpg",$i);
		$cmd =<<EOS;
convert -size 640x480 xc:white -gravity center -weight 700 -pointsize 20 -annotate 0 "$txt" $filename
EOS
			`$cmd`;
			++$i;
		}
	}
	@files = glob("/tmp/jpgs/*.jpg");
	$i = 0;
	for $file (@files)
	{
		print "processing $file\n"
			if (++$i % 20) == 0;
		`cat $file > $outpipe`;
		sleep(1/$fps);
	}
}
elsif($command eq 'doit4')
{
	$containername = shift;

	if(! -d '/tmp/jpgs')
	{
		`mkdir -p /tmp/jpgs`;
		chdir '/tmp/jpgs';
		$i = 1;
		for(;$i<=1000;)
		{
			$txt = sprintf("hello world # %05d",$i);
			$filename = sprintf("testimage%05d.jpg",$i);
		$cmd =<<EOS;
convert -size 640x480 xc:white -gravity center -weight 700 -pointsize 20 -annotate 0 "$txt" $filename
EOS
			`$cmd`;
			++$i;
		}
	}

	$t1 = time;
	$ret = `./$0 doit3 $containername 1000`;
	$t2 = time;
	$dur = $t2 - $t1;
	$fps = 1000 / $dur;
	$inpipe2Option = "--inpipe2"
		if $options{inpipe2};

	print "execution time to stream 1000 frames is $dur: $fps fps\n";
}
elsif($command eq 'convert1')
{
	`rm -rf /tmp/jpgs`;
	$t1 = time;
	if(! -d '/tmp/jpgs')
	{
		`mkdir -p /tmp/jpgs`;
		chdir '/tmp/jpgs';
		$i = 1;
		$frames = 100;
		for(;$i<=$frames;)
		{
			$txt = sprintf("hello world # %05d",$i);
			$filename = sprintf("testimage%05d.jpg",$i);
		$cmd =<<EOS;
convert -size 640x480 xc:white -gravity center -weight 700 -pointsize 20 -annotate 0 "$txt" $filename
EOS
			`$cmd`;
			++$i;
		}
	}
	$t2 = time;
	$dur = $t2 - $t1;
	$fps = $frames / $dur;
	print "execution time to stream $frames frames is $dur: $fps fps\n";
}
else
{
	confess $usage;
}

