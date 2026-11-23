#include "trackercfgfile.h"

#include "sdfile.h"

#define SETTINGS_FILE SDFILE_DIR "/tracker.cfg"
#define FILE_ROOM     32 /* one short line */

void trackercfgfile_load(trackercfg_t *cfg)
{
  char text[FILE_ROOM];
  size_t size;
  if (sdfile_read("tracker", SETTINGS_FILE, text, sizeof(text), &size))
    trackercfg_parse(cfg, text, size);
}

bool trackercfgfile_save(const trackercfg_t *cfg)
{
  char text[FILE_ROOM];
  size_t length = trackercfg_format(cfg, text, sizeof(text));
  return sdfile_write("tracker", SETTINGS_FILE, text, length);
}
