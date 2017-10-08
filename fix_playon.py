import subprocess, os, json, shutil, time, logging, uuid
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

      # logging
      session_uuid = str(uuid.uuid4())
      fmt = '%%(asctime)-15s [%s] %%(message)s' % session_uuid[:6]
      logging.basicConfig(level=logging.INFO, format=fmt, filename="%s/fix_playon.log" % self.base_dir)


      # have some code here to allow comments in the json settings file
      settings_array = open('fix_playon_config.ini').readlines()
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


      # do the things
      self.action = "process"
      while self.action != "done":
        self.scan_watch_dir()


  def get_meta(self,filename):
    cmd_list = [self.settings['ffprobe'],'-v','quiet','-print_format','json','-show_chapters','-show_format',filename]
    result = subprocess.Popen(cmd_list, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    logging.info("FFProbe command: %s" % " ".join(cmd_list))
    raw_string = result.stdout.read()
    return json.loads(raw_string)


  def convert(self, root_dir, item, out_dir):
    filename = '%s/%s' % (root_dir, item)
    file_meta = self.get_meta(filename)
    cut_times = []
    file_list = []
    concat_file = ''
    chapter_list = file_meta['chapters']
    try:
      provider = file_meta['format']['tags']['ProviderName']
    except:
      provider = "default"
    service = self.settings['services'][provider]

    for chapter in chapter_list:
      if chapter['start_time'] == '0.000000' and float(chapter['end_time']) < 10.0:
        continue
      if chapter['tags']['title'] == 'Advertisement':
        continue
      if chapter['start_time'] == '0.000000':
        cut_times.append([service['start_cut'], float(chapter['end_time'])])
      else:
        cut_times.append([float(chapter['start_time']), float(chapter['end_time'])])

    if service["use_comskip"].lower() == "true":
      cut_times = self.use_comskip(root_dir, item, file_meta)
      logging.info(chapter_list)
    if chapter_list == []: #netflix and HBOGO movies don't have chapters
      if not service == "":
        end_time = float(file_meta['format']['duration']) - service['end_cut']
        cut_times = [[service['start_cut'],end_time]]
      else:
        end_time = float(file_meta['format']['duration']) - 10
        cut_times =   [['6.0',end_time]]
    else:
      end_segment = cut_times.pop()
      end_segment[1] = float(end_segment[1]) - service['end_cut']
      cut_times.append(end_segment)

    count = 0
    splitfile = item.split('.mp4')[0]
    concat_file_name = '%s/%s.concat.list' % (self.work_dir,splitfile)
    concat_file = open(concat_file_name, 'w')
    for segment in cut_times:
      outfile = '%s/%s-%s.mp4' % (self.work_dir,splitfile,count)
      file_list.append(outfile)
      concat_file.write("file '%s-%s.mp4'\n" % (splitfile,count))
      cmd_list = [self.settings['ffmpeg'],'-i','%s' % filename, '-map_metadata', '-1', '-ss', str(segment[0]), '-to', str(segment[1]), '-c', 'copy', '%s' %  outfile]
      logging.info("FFMpeg command: %s" % " ".join(cmd_list))
      result = subprocess.Popen(cmd_list, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
      raw_string = result.communicate()
      count += 1
    concat_file.close()

    final_out = '%s/%s.mp4' % (out_dir,splitfile)
    if len(cut_times) == 1:
      shutil.move('%s/%s-0.mp4' % (self.work_dir,splitfile), final_out)
    else:
      cmd_list = [self.settings['ffmpeg'],'-f','concat', '-safe', '0', '-i', '%s' % concat_file_name, '-c', 'copy', '%s' %  final_out]
      logging.info("FFMpeg command: %s" % " ".join(cmd_list))
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
          #if item == "Unforgettable.mp4":
            #print root
          self.convert(root, item, out_dir)
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
    if self.settings['destroy_cut_files'].lower() == "false":
      return
    for item in listdir(self.work_dir):
      try:
        os.unlink('%s/%s' % (self.work_dir,item))
      except:
        pass

  def use_comskip(self, root_dir, item, file_meta):
    filename = '%s/%s' % (root_dir, item)
    cmd = [self.settings['comskip'], '--output', root_dir, '--ini', self.settings["comskip_ini"], filename]
    logging.info('[comskip] Command: %s' % " ".join(cmd))
    #subprocess.call(cmd)

    edl_file = '%s/%s.edl' % (root_dir,item.split(".mp4")[0])
    logging.info('Using EDL: ' + edl_file)
    segments = []
    prev_segment_end = 0.0
    if os.path.exists(edl_file):
      with open(edl_file, 'rb') as edl:

        # EDL contains segments we need to drop, so chain those together into segments to keep.
        for segment in edl:
          start, end, something = segment.split()
          if float(start) == 0.0:
            logging.info('Start of file is junk, skipping this segment...')
          else:
            keep_segment = [float(prev_segment_end), float(start)]
            logging.info('Keeping segment from %s to %s...' % (keep_segment[0], keep_segment[1]))
            segments.append(keep_segment)
          prev_segment_end = end

    # Write the final keep segment from the end of the last commercial break to the end of the file.
    keep_segment = [float(prev_segment_end), float(file_meta['format']['duration'])]
    logging.info('Keeping segment from %s to the end of the file...' % prev_segment_end)
    segments.append(keep_segment)
    return segments


if __name__ == "__main__":
  fix_playon()
