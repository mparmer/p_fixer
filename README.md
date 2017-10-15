This project requires Python 2.7, and FFMpeg, Comskip is optional

You can customize cut times and such in the fix_playon_config.ini file.  If you have a new service that is not listed in the config, please add it and add the cut times you wish to remove from the beginning and end of the file.. Comskip may or may not work depending on the file.  I had trouble with VUDU files as they could not find a logo and require extra tuning to use Comskip.  If you wish to analyze a file yourself, simply look in the output log file for the commands, and run the ffprobe command for the file you are trying to fix.


