#!/usr/bin/perl
use Data::Dumper;
use Carp;
use Time::HiRes qw(time sleep);
use Getopt::Long;
use IO::Select;
use Fcntl;
use File::Spec;
use lib "dockerpipes"; 
use DockerPipes;

$usage = <<EOS;
$0 cmd options
	valid commands:
		runtrainer dir
		runapp dir [programname] port
			defaults to: http://localhost:6001/status.html	
			where dir contains .h5, .npy, input.mp4, 
			programname is the analytics code to execute
				TGPOC1
					tail gating demo 1: ./run.pl runapp e2e_ffserver_tgpoc1.py 
        face port
        face port1 port2
		stopapp  dir
		installapp	
			to support myhub.pl
	options:
EOS

GetOptions(
	'mode=s' => \$options{mode},
	'booleanparam' => \$options{booleanparam},
	);

confess $usage
	if !@ARGV;

$command = shift;


if($command eq 'runapp')
{
	$appdata = shift;
        $dirname = $appdata;
        $port = shift;
	confess $usage
		if !($appdata && $port);

	$programname = shift;
	print "programname: $programname\n";
	$appdata = File::Spec->rel2abs($appdata);

	confess "dir: $appdata does not exist"
		if !-d $appdata;


	print "appdata: $appdata\n";
        $input_containername = $dirname."_df01";
 	$output_containername = $dirname."_sv01";
        
	print `cd sv01 && ./run.pl start2 $output_containername 6 $port`;
	sleep(5);
	$op = DockerPipes->load($output_containername);
	$outpipe = $op->{inpipe2_jpg};
	confess "can't find input pipe for $output_containername"
		if !$outpipe;
	`mkfifo -m 666 $outpipe`;
	print "fifo created\n";
	print `cd DeepFusion001 && ./run.pl start $input_containername $appdata $output_containername $programname`;
	print "output_containername: $output_containername\n";

#	print `cd sv01 && ./run.pl container sv01 6001`;
#	print `cd sv01 && ./run.pl exec sv01 inpipe2`;

}

elsif($command eq 'face'){
    $port = shift;
	confess $usage
		if !($port);

    $output_containername = 'svtt2';
    print `cd ../sv01 && ./run.pl start2 $output_containername 16 $port`;
	sleep(5);

	$op = DockerPipes->load($output_containername);
	$outpipe = $op->{inpipe2_jpg};
	confess "can't find input pipe for $output_containername"
		if !$outpipe;

	`mkfifo -m 666 $outpipe`
		if ! -e $outpipe;

	sleep(3);
    print `cd ../cv && python cv1.py --outpipe $outpipe --file coop1.mp4`;
}

elsif($command eq 'face2'){
    $port1 = shift;
	confess $usage
		if !($port1);
	$port2 = shift;
	confess $usage
		if !($port2);

    $output_containername1 = 'svtt1';
    print `cd ../sv01 && ./run.pl start2 $output_containername1 16 $port1`;
    $output_containername2 = 'svtt2';
    print `cd ../sv01 && ./run.pl start2 $output_containername2 16 $port2`;
	sleep(5);

    #
	$op1 = DockerPipes->load($output_containername1);
	$outpipe1 = $op1->{inpipe2_jpg};
	confess "can't find input pipe for $output_containername1"
		if !$outpipe1;

	`mkfifo -m 666 $outpipe1`
		if ! -e $outpipe1;
	#
	$op2 = DockerPipes->load($output_containername2);
	$outpipe2 = $op2->{inpipe2_jpg};
	confess "can't find input pipe for $output_containername2"
		if !$outpipe2;

	`mkfifo -m 666 $outpipe2`
		if ! -e $outpipe2;

#	sleep(3);
    `cd ../cv && python cv1.py --outpipe1 $outpipe1 --outpipe2 $outpipe2`;
}

elsif($command eq 'runtrainer')
{
	$appdata = shift;
	confess $usage
		if !$appdata;

	$programname = shift;

	$appdata = File::Spec->rel2abs($appdata);

	confess "dir: $appdata does not exist"
		if !-d $appdata;

	print `cd DeepFusion001 && ./run.pl start trainer $appdata nooutput trainer`;
	sleep(20);
	print `docker exec -d trainer bash -c "apt-get install -y graphviz"`;
#	print `cd sv01 && ./run.pl container sv01 6001`;
#	print `cd sv01 && ./run.pl exec sv01 inpipe2`;

}
elsif($command eq 'stopapp')
{       
        $dir = shift;

        confess $usage
                if !$dir;

        $dirname = $dir;      
	$output_containername = $dirname."_sv01";
        $input_containername = $dirname."_df01";

	$op = DockerPipes->load($output_containername);
	$outpipe = $op->{inpipe2_jpg};
        print "$outpipe\n";
	confess "can't find input pipe for $output_containername"
		if !$outpipe;
	`rm -f $outpipe`;
	print `docker rm -f $input_containername $output_containername`;
}
elsif($command eq 'installapp')
{
	`cp $0 .`;
	`rsync -rvztu $ENV{HGDIR}/docker/myhub/$output_containername .`;
	`rsync -rvztu $ENV{HGDIR}/docker/myhub/DeepFusion001 .`;
	confess "DeepFusion001 directory doesn't exist!"
		if !-d 'DeepFusion001';
	`rsync $ENV{HGDIR}/ml_data/DeepFusion/coop2.tgz.pl .`;
	`rsync $ENV{HGDIR}/ml_data/DeepFusion/TGX01.tgz.pl .`;
	`rsync $ENV{HGDIR}/ml_data/DeepFusion/TGX02.tgz.pl .`;
	`./coop2.tgz.pl selfinstall`;
	`./TGX01.tgz.pl selfinstall`;
	`./TGX02.tgz.pl selfinstall`;
	`rm coop2.tgz.pl TGX01.tgz.pl TGX02.tgz.pl`;
}
else
{
	confess $usage;
}

