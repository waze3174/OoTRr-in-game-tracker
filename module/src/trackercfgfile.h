/* The tracker's setting in ootrTracker/tracker.cfg on the SD card (sdfile.c), as the postcard's are kept. */
#ifndef TRACKERCFGFILE_H
#define TRACKERCFGFILE_H

#include <stdbool.h>

#include "trackercfg.h"

/* Reads the file over `cfg`; a missing or damaged file leaves it as it was. Game thread, once, after the game's
 * files are mounted. */
void trackercfgfile_load(trackercfg_t *cfg);
/* Writes the file again; false (logged) if there is no SD card or the write failed. */
bool trackercfgfile_save(const trackercfg_t *cfg);

#endif
