package DockerPipes;
require Exporter;
use Data::Dumper;
use Carp;
use File::Temp qw(tempfile);
@ISA = qw(Exporter);
@EXPORT = qw( 
	); 

sub new
{
	my $class = shift;
	my %params = @_;
	my $self = \%params;
	bless $self, $class;

	$self->{share_basedir} = '/tmp/DockerPipes';
	$self->{appname} = 'defaultapp';

	#verify key parameters here
	return $self;
}

sub initShare
{
	my($self,$containername) = @_;
	confess "containername parameter missing"
		if !$containername;

	$self->{containername} = $containername;
	$self->{myshare} = "$self->{share_basedir}/$self->{appname}/$self->{containername}";
	`mkdir -p $self->{myshare}`;

	$self->{configfiles_dir} = "$self->{share_basedir}/configs";
	`mkdir -p $self->{configfiles_dir}`;

	$self->{configfilename} = "$self->{configfiles_dir}/$self->{containername}\.pl"; 
}

sub addFIFO
{
	my($self) = @_;
	$c{in001} = "$c{myshare}/in001";
	$c{out001} = "$c{myshare}/outpipe.jpg";
	`mkfifo -m 666 $c{in001}`;
	`mkfifo -m 666 $c{out001}`;
	`mkfifo -m 666 $options{share_basedir}/outpipe.jpg`; #TODO use config 
}


sub writeConfig
{
	my($self) = @_;
	my %self = %$self;
	open $f, ">$self->{configfilename}";
	print Data::Dumper->Dump([\%self], ['cfg']);
	print $f Data::Dumper->Dump([\%self], ['cfg']);
	close $f;
}

sub load 
{
	my($class, $containername) = @_;
	my $self1 = DockerPipes->new();
	$self1->initShare($containername);
	print "configfilename: $self1->{configfilename}\n";
	return 0
		if ! -e $self1->{configfilename};

	do "$self1->{configfilename}";
	print Data::Dumper->Dump([$cfg], ['cfg']);
	bless $cfg, $class;
	return $cfg;
}

sub create 
{
	my($class, $containername) = @_;
	my $self = DockerPipes->new();
	$self->initShare($containername);
	$self->writeConfig();
	return $self;
}

1;

