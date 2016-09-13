ffserver -f fftest.conf
ffmpeg -r 2 -s 640x480 -i outpipe http://localhost:5001/feed1.ffm

