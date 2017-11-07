import subprocess, os, json, shutil, time, logging, uuid
from os import system, walk, makedirs, listdir, renames
from sys import exit


class auto_combine:
  def __init__(self):
    self.base_dir = os.getcwd()
    self.work_dir = '%s/temp_work' % self.base_dir
    if os.path.exists(self.work_dir) == False:
      try:
        os.mkdir(self.work_dir)
      except:
        pass

    # logging
    session_uuid = str(uuid.uuid4())
    fmt = '%%(asctime)-15s [%s] %%(message)s' % session_uuid[:6]
    logging.basicConfig(level=logging.INFO, format=fmt, filename="%s/file_combiner.log" % self.base_dir)


    # have some code here to allow comments in the json settings file
    settings_array = open('file_combiner.ini').readlines()
    settings_json = ""
    for line in settings_array:
      if not line.startswith('#'):
        settings_json += line
    self.settings =  json.loads(settings_json)

    if self.settings["console_logging"].lower() == "true":
      console = logging.StreamHandler()
      console.setLevel(logging.INFO)
      formatter = logging.Formatter('%(message)s')
      console.setFormatter(formatter)
      logging.getLogger('').addHandler(console)

    self.file_hash = {}
    # do the things
    self.action = "process"
    while self.action != "done":
      self.scan_watch_dir()

  def scan_watch_dir(self):
    for root, dirs, files in walk(self.settings['watch_dir']):
      if files == []:
        continue
      for item in files:
        if item.endswith('.mp4'):
          print item
          key = item[0:40]
          val = item
          try:
            self.file_hash[key].append(val)
          except:
            self.file_hash[key] = [val]
          # check to make sure the file modification time is older than 5 minutes
    self.process_files()
    #when all dirs and files have been processed, set as done, and script will exit
    print "made it to the done"
    self.action = "done"

  def process_files(self):
    for key,vals in self.file_hash.items():
      final_out = '%s/%s.mp4' % (self.settings['out_dir'],vals[0].split('_Act')[0].split("\\")[-1].split("/")[-1])
      if os.path.exists(final_out): # if the out file already exists, skip it and go on
        continue
      concat_file_name = '%s/%s.concat.list' % (self.settings['watch_dir'],key.replace(" ","_").replace("'",""))
      concat_file = open(concat_file_name, 'w')
      for item in vals:
        concat_file.write("file '%s'\n" % item)
      concat_file.close()
      cmd_list = [self.settings['ffmpeg'],'-f','concat', '-safe', '0', '-i', '%s' % concat_file_name, '-c', 'copy', '%s' %  final_out]
      logging.info("FFMpeg command: %s" % " ".join(cmd_list))
      result = subprocess.Popen(cmd_list, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
      raw_string = result.communicate()
#.\youtube-dl.exe -v --ap-username yourcomcastusername --ap-password yourcomcastpassword --ap-mso Comcast_SSO http://www.cc.com/episodes/jpstyr/idiotsitter-pilot-season-1-ep-101

#.\youtube-dl.exe -v --ap-username parmer09 --ap-password 1bowling --ap-mso Comcast_SSO
if __name__ == "__main__":
  auto_combine()
