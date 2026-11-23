/* The tracker's own setting that isn't the postcard's or the console's: which names the checks are shown by
 * (the community's, or the randomizer's own). Kept in ootrTracker/tracker.cfg on the SD card (trackercfgfile.c).
 * Pure: the drawing is trackerui.c's. */
#ifndef TRACKERCFG_H
#define TRACKERCFG_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum { NAMES_COMMUNITY, NAMES_RANDOMIZER, NAMES_CHOICE_COUNT } names_choice_t;

typedef struct {
  uint8_t names; /* names_choice_t */
} trackercfg_t;

/* The community's names. */
trackercfg_t trackercfg_defaults(void);
const char *trackercfg_names_label(void);
/* The value as the Settings page shows it ("Community", "Randomizer"). */
const char *trackercfg_names_text(const trackercfg_t *cfg);
/* Whether the checks are shown by the randomizer's own names. */
bool trackercfg_randomizer_names(const trackercfg_t *cfg);
/* The other value (there are two: either direction). */
void trackercfg_step_names(trackercfg_t *cfg, int direction);

/* The file's text: `names=0` (community) or `names=1` (randomizer). Returns its length, cut to room - 1. */
size_t trackercfg_format(const trackercfg_t *cfg, char *out, size_t room);
/* Reads what the text sets, on top of `cfg`; a line that isn't a known name with a valid value is skipped, so a
 * damaged or empty file leaves the setting as it was. */
void trackercfg_parse(trackercfg_t *cfg, const char *text, size_t size);

#endif
