#include "trackercfg.h"

#include "cfgtext.h"

#define NAMES_SETTING 0 /* the file's names, in order: only `names` for now */

static const char *const file_names[] = { "names" };
static const char *const names_texts[NAMES_CHOICE_COUNT] = {
  [NAMES_COMMUNITY] = "Community", [NAMES_RANDOMIZER] = "Randomizer",
};

trackercfg_t trackercfg_defaults(void)
{
  return (trackercfg_t){ .names = NAMES_COMMUNITY };
}

const char *trackercfg_names_label(void)
{
  return "Names";
}

const char *trackercfg_names_text(const trackercfg_t *cfg)
{
  return names_texts[cfg->names % NAMES_CHOICE_COUNT];
}

bool trackercfg_randomizer_names(const trackercfg_t *cfg)
{
  return cfg->names == NAMES_RANDOMIZER;
}

void trackercfg_step_names(trackercfg_t *cfg, int direction)
{
  (void)direction; /* two values: the other one either way */
  cfg->names = cfg->names == NAMES_COMMUNITY ? NAMES_RANDOMIZER : NAMES_COMMUNITY;
}

size_t trackercfg_format(const trackercfg_t *cfg, char *out, size_t room)
{
  size_t length = cfgtext_line(out, room, 0, file_names[NAMES_SETTING], cfg->names);
  if (room)
    out[length] = 0;
  return length;
}

static bool apply_value(void *to, int name, uint32_t value)
{
  trackercfg_t *cfg = to;
  if (name != NAMES_SETTING || value >= NAMES_CHOICE_COUNT)
    return false;
  cfg->names = (uint8_t)value;
  return true;
}

void trackercfg_parse(trackercfg_t *cfg, const char *text, size_t size)
{
  cfgtext_parse(text, size, file_names, 1, apply_value, cfg);
}
