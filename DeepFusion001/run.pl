#!/usr/bin/perl
use Data::Dumper;
use Carp;
use Time::HiRes qw(time sleep);
use Getopt::Long;
use File::Spec;
use lib "../dockerpipes";
use DockerPipes;

$default_programname = 'e2e_ffserver.py';
$usage = <<EOS;
$0 cmd options
	valid commands:
		start containername workdir output_containername [programname]
			runs config.json in workdir 
			output goes to output_containername via Unix FIFO
			where programname = name of analytics program to execute
			use programname for analysis defaults to: $default_programname
			
		startFlask
			same as start only using Flask for output

		container containername [workdir]
			where workdir contains config.json, .h5, .npy, ...
			workdir must be an absolute path (for now)

		runanalytics outpipe [programname]
			run inside the docker container to execute the analytics engine
			on workdir/config.json
			use programname for analysis 

# private methods  
		get datasetname
			datasetname does not include .tgz.pl

		getdefault
			which is coop2 dataset

	options:
EOS

GetOptions(
	'mode=s' => \$options{mode},
	'booleanparam' => \$options{booleanparam}
	);

confess $usage
	if !@ARGV;

$command = shift;

if($command eq 'container')
{
	$ds = DockerPipes->create(shift);
	confess $usage
		if !$ds;

	$workdir = shift;
	$workVolumeSubcmd = "--volume=$workdir:/root/DeepFusion001/workdir"
		if $workdir;
	
	$ds->{workdir} = $workdir;

	`docker rm -f $ds->{containername}`;


	$cmd =<<EOS;
nvidia-docker run -d --volume=\$(pwd)/../dockerpipes:/root/dockerpipes --volume=\$(pwd):/root/DeepFusion001 $workVolumeSubcmd --volume=$ds->{share_basedir}:$ds->{share_basedir} --workdir=/root/DeepFusion001 --name=$ds->{containername} hmlatapie/rr_caffe /bin/bash -c "while true; do date; sleep 3600; done"
EOS

	print `$cmd`;
	$ds->writeConfig();	
}
elsif($command eq 'start')
{
	$containername = shift;
	$workdir = shift;
	$workdir = File::Spec->rel2abs($workdir);
	$output_containername = shift;
	confess $usage
		if !$containername || !$workdir || !-d$workdir || !$output_containername;

	$programname = shift;
	$programname = $default_programname
		if !$programname;

	if($output_containername ne 'nooutput')
	{
	$op = DockerPipes->load($output_containername);
	$outpipe = $op->{inpipe2_jpg};
	confess "can't find input pipe for $output_containername"
		if !$outpipe;
	}
	print `./run.pl container $containername $workdir`;
	
	print "111111111111111111111111111111111111111111111111111$outpipe\n";
	
	print `docker exec -d $containername /bin/bash -c "./run.pl runanalytics $outpipe $programname"`
		if $output_containername ne 'nooutput';

}
elsif($command eq 'runanalytics')
{
	$outpipe = shift;
	$programname = shift;
	confess $usage
		if !$outpipe || !$programname;

	if(-e $programname)
	{
		$cmd = "python $programname --config workdir/config.json --cam 2 --gpu 3 --outpipe $outpipe";
		open $f, "$cmd |";
		print
			while <$f>;
	}
}
elsif($command eq 'get')
{
	$filename = shift;
	$filename .= '.tgz.pl';

	print `$ENV{HGDIR}/ml_data/DeepFusion/$filename selfinstall`;
}
elsif($command eq 'getdefault')
{
	print `$0 get coop2`;
}
else
{
	confess $usage;
}

