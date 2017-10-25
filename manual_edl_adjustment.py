
class manual_fix:
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
    settings_array = open('manual_edl_config.ini').readlines()
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

  def scan_watch_dir(self):
    for root, dirs, files in walk(self.settings['watch_dir']):
      if files == []:
        continue
      out_dir = self.settings['watch_dir']
      for item in files:
        if item.endswith('.mp4') or item.endswith('.ts'):
          print start_file
          # check to make sure the file modification time is older than 5 minutes
          if (os.stat(start_file)[8] + 300) > time.time():
            continue # when it is not, skip this file
          self.convert(root, item, out_dir)
    #when all dirs and files have been processed, set as done, and script will exit
    print "made it to the done"
    self.action = "done"

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
    if item.endswith(".mp4"):
      edl_file = '%s/%s.edl' % (root_dir,item.split(".mp4")[0])
    if item.endswith(".ts"):
      edl_file = '%s/%s.edl' % (root_dir,item.split(".ts")[0])
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
    else:
      print "Uh Oh, couldn't find EDL file %s" % edl_file

    # Write the final keep segment from the end of the last commercial break to the end of the file.
    keep_segment = [float(prev_segment_end), float(file_meta['format']['duration'])]
    logging.info('Keeping segment from %s to the end of the file...' % prev_segment_end)
    segments.append(keep_segment)
    cut_times = segments

    count = 0
    suffix = ".mp4"
    if item.endswith(".ts"):
      suffix = ".ts"

    splitfile = item.split(suffix)[0]
    final_out = '%s/%s-fixed%s' % (out_dir,splitfile,suffix)
    concat_file_name = '%s/%s.concat.list' % (self.work_dir,splitfile)
    concat_file = open(concat_file_name, 'w')
    for segment in cut_times:
      outfile = '%s/%s-%s' % (self.work_dir,splitfile,count)
      if len(cut_times) == 1:
        outfile = final_out
      file_list.append(outfile)
      concat_file.write("file '%s-%s'\n" % (splitfile,count))
      cmd_list = [self.settings['ffmpeg'],'-i','%s' % filename, '-map_metadata', '-1', '-ss', str(segment[0]), '-to', str(segment[1]), '-c', 'copy', '%s' %  outfile]
      logging.info("FFMpeg command: %s" % " ".join(cmd_list))
      result = subprocess.Popen(cmd_list, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
      raw_string = result.communicate()
      count += 1
    concat_file.close()

    if len(cut_times) > 1:
      cmd_list = [self.settings['ffmpeg'],'-f','concat', '-safe', '0', '-i', '%s' % concat_file_name, '-c', 'copy', '%s' %  final_out]
      logging.info("FFMpeg command: %s" % " ".join(cmd_list))
      result = subprocess.Popen(cmd_list, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
      raw_string = result.communicate()

    #self.destroy_cut_files()

  def destroy_cut_files(self):
    if self.settings['destroy_cut_files'].lower() == "false":
      return
    for item in listdir(self.work_dir):
      try:
        os.unlink('%s/%s' % (self.work_dir,item))
      except:
        pass



if __name__ == "__main__":
  manual_fix()

