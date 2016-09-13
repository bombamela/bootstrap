#!/usr/bin/perl
use Data::Dumper;
use Carp;
use Time::HiRes qw(time sleep);
use Getopt::Long;
use IO::Select;
use Fcntl;
use File::Spec;
use lib "../dockerpipes";
use DockerPipes;


	$output_containername = 'svtt2';

	$op = DockerPipes->load($output_containername);
	$outpipe = $op->{inpipe2_jpg};
	confess "can't find input pipe for $output_containername"
		if !$outpipe;

	`mkfifo -m 666 $outpipe`
		if ! -e $outpipe;
	
	while (1){
		`cat ./temp.jpg > $outpipe`;
		sleep(1.0/16);
	}
