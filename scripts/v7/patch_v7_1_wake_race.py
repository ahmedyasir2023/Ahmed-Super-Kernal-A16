#!/usr/bin/env python3
"""V7.1: guard against stale 600s timers during rapid OFF/ON/OFF."""
from pathlib import Path
p = Path(__file__).resolve().parents[2] / "kernel/drivers/cpufreq/cpu-boost.c"
s = p.read_text()

def replace(old, new, label):
    global s
    assert s.count(old) == 1, f"V7.1 layout changed at {label}"
    s = s.replace(old, new, 1)

replace("#include <linux/notifier.h>\n",
        "#include <linux/notifier.h>\n#include <linux/jiffies.h>\n", "jiffies include")
replace(
    "static struct delayed_work ay_deepdoze_timer;\n",
    """static unsigned long ay_deepdoze_last_blank;
static struct delayed_work ay_deepdoze_timer;
""",
    "panel deadline timestamp",
)
replace(
    """    WRITE_ONCE(ay_deepdoze_active, true);
    /* A display unblank may race the timer. Never retain a stale cap. */
""",
    """    /* Delayed work from an older screen-off interval can finish after the
     * panel was unblanked and quickly reblanked. Do not engage a cap until
     * the MOST RECENT blank has lasted at least 600 seconds.
     */
    {
        unsigned long due = READ_ONCE(ay_deepdoze_last_blank) +
                            msecs_to_jiffies(600000);

        if (time_before(jiffies, due)) {
            mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,
                             due - jiffies);
            return;
        }
    }
    if (READ_ONCE(ay_screen_on))
        return;
    WRITE_ONCE(ay_deepdoze_active, true);
    /* A display unblank may race the timer. Never retain a stale cap. */
""",
    "reject stale expiration",
)
replace(
    """            mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
            if (READ_ONCE(ay_deepdoze_enabled))
""",
    """            mod_delayed_work(cpu_boost_wq, &input_boost_rem, 0);
            WRITE_ONCE(ay_deepdoze_last_blank, jiffies);
            if (READ_ONCE(ay_deepdoze_enabled))
""",
    "arm from latest blank",
)
assert s.count("msecs_to_jiffies(600000)") == 2
assert s.count("WRITE_ONCE(ay_deepdoze_last_blank, jiffies)") == 1
assert "policy->max =" not in s
p.write_text(s)
print("V7.1: last-blank 600s invariant staged; no extra wake timers.")
