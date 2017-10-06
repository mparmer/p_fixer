import subprocess, os, json, shutil, time
from os import system, walk, makedirs, listdir, renames


class fix_playon:
  def __init__(self):
      self.base_dir = os.getcwd()
      self.work_dir = '%s/temp_work' % self.base_dir
      if os.path.exists(self.work_dir) == False:
        try:
          os.mkdir(self.work_dir)
        except:
          pass

      # have some code here to allow comments in the json settings file
      settings_array = open('fix_playon_config.ini').readlines()
      settings_json = ""
      for line in settings_array:
        if not line.startswith('#'):
          settings_json += line
      self.settings =  json.loads(settings_json)

      self.action = "process"
      while self.action != "done":
        self.scan_watch_dir()


  def get_meta(self,filename):
    result = subprocess.Popen([self.settings['ffprobe'],'-v','quiet','-print_format','json','-show_chapters','-show_format',filename], stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    raw_string = result.stdout.read()
    return json.loads(raw_string)


  def convert(self, filename, out_dir):
    file_meta = self.get_meta(filename)
    cut_times = []
    file_list = []
    concat_file = ''
    chapter_list = file_meta['chapters']
    try:
      provider = file_meta['format']['tags']['ProviderName']
    except:
      provider = "default"
    for chapter in chapter_list:
      if chapter['start_time'] == '0.000000' and float(chapter['start_time']) < 10.0:
        continue
      if chapter['tags']['title'] == 'Advertisement':
        continue
      cut_times.append([float(chapter['start_time']), float(chapter['end_time'])])
    if provider == "Crackle":
      #put in comskip code
      pass
    if chapter_list == []: #netflix and HBOGO movies don't have chapters
      service = self.settings['services'][provider]
      if not service == "":
        end_time = float(file_meta['format']['duration']) - service['end_cut']
        cut_times = [[service['start_cut'],end_time]]
      else:
        end_time = float(file_meta['format']['duration']) - 10
        cut_times =   [['6.0',end_time]]
    else:
      end_segment = cut_times.pop()
      end_segment[1] = float(end_segment[1]) - 10
      cut_times.append(end_segment)

    count = 0
    splitfile = filename.split("\\")[-1].split('.mp4')[0]
    concat_file_name = '%s/%s.concat.list' % (self.work_dir,splitfile)
    concat_file = open(concat_file_name, 'w')
    for segment in cut_times:
      outfile = '%s/%s-%s.mp4' % (self.work_dir,splitfile,count)
      file_list.append(outfile)
      concat_file.write("file '%s-%s.mp4'\n" % (splitfile,count))
      cmd_list = [self.settings['ffmpeg'],'-i','%s' % filename, '-map_metadata', '-1', '-ss', str(segment[0]), '-to', str(segment[1]), '-c', 'copy', '%s' %  outfile]
      result = subprocess.Popen(cmd_list, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
      raw_string = result.communicate()
      count += 1
    concat_file.close()

    final_out = '%s/%s.mp4' % (out_dir,splitfile)
    if len(cut_times) == 1:
      shutil.move('%s/%s-0.mp4' % (self.work_dir,splitfile), final_out)
    else:
      cmd_list = [self.settings['ffmpeg'],'-f','concat', '-safe', '0', '-i', '%s' % concat_file_name, '-c', 'copy', '%s' %  final_out]
      print cmd_list
      result = subprocess.Popen(cmd_list, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
      raw_string = result.communicate()

    self.destroy_cut_files()


  def scan_watch_dir(self):
    for root, dirs, files in walk(self.settings['watch_dir']):
      if files == []:
        continue
      out_dir = '%s%s' % (self.settings['out_dir'],root.split(self.settings['watch_dir'])[1])
      if os.path.exists(out_dir) == False:
        try:
          makedirs(out_dir)
        except:
          pass
      for item in files:
        if item.endswith('.mp4'):
          end_file = start_file = '%s\%s' % (root, item)
          print start_file
          # check to make sure the file modification time is older than 5 minutes
          if (os.stat(start_file)[8] + 300) > time.time():
            continue # when it is not, skip this file

          end_file = end_file.replace("'","").replace('"',"")
          if os.path.exists('%s/%s' % (out_dir, item)): # if the out file already exists, skip it and go on
            continue
          if end_file != start_file:
            self.fix_dirs_and_files(root)
            print start_file
            print end_file

            print "fixed files and dirs in %s, now retrying" % root
            return "try again"
          #if item == "Bob's Burgers - s07e18 - The Laser-Inth.mp4":
            #print root
          print "made it to the convert"
          self.convert('%s\%s' % (root, item), out_dir)
    #when all dirs and files have been processed, set as done, and script will exit
    print "made it to the done"
    self.action = "done"


  def fix_dirs_and_files(self, root_dir):
    new_root = root_dir.replace("'","").replace('"',"")
    if new_root != root_dir:
      if os.path.exists(new_root) == False:
        makedirs(new_root)
    for file in listdir(root_dir):
      if file.count("'") > 0:
        renames("%s/%s" % (root_dir,file), "%s/%s" % (new_root,file.replace("'","").replace('"',"")))


  def destroy_cut_files(self):
    if self.settings['destroy_cut_files'] == "False":
      return
    for item in listdir(self.work_dir):
      try:
        os.unlink('%s/%s' % (self.work_dir,item))
      except:
        pass


if __name__ == "__main__":
  fix_playon()
