#!/usr/bin/perl
use Data::Dumper;
use Carp;
use Time::HiRes qw(time sleep);
use Getopt::Long;
use DockerPipes;

$usage = <<EOS;
$0 cmd options
	valid commands:

		createobject
			test object creation


	options:
EOS

GetOptions(
	'stringparam=s' => \$options{stringparam},
	'booleanparam' => \$options{booleanparam}
	);

confess $usage
	if !@ARGV;

$command = shift;

if($command eq 'createobject')
{
	$t = DockerPipes->new();
	print Dumper($t);
	print "\nnow test write for container: testzzz\n";
	$t->initShare('testzzz');
	$t->writeConfig();
	print "\nnow test create for container: test2zzz\n";
	$t2 = DockerPipes->create('test2zzz');
	print "\nnow test read for containers: testzzz,test2zzz\n";
	$t1 = DockerPipes->load('testzzz');
	$t2 = DockerPipes->load('test2zzz');
	print "\nt1:" . Dumper($t1) . "\n";
	print "\nt2:" . Dumper($t2) . "\n";

	$t = DockerPipes->load('asdf');
	if($t)
	{
		print "load non-existent config test failed\n";
	}
	else
	{
		print "passed non-existing config load test\n";
	}
}
else
{
	confess $usage;
}

