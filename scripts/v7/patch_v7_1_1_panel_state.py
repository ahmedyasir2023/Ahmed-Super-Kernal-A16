#!/usr/bin/env python3
"""V7.1.1: continuously track display state even if saver is disabled.

Fix: the original V6 early return from the panel notifier when the writable
ay_screenoff_saver parameter is false can leave ay_screen_on permanently
false after a subsequent unblank. Preserve accurate panel state, but arm
the deep-doze timer only while the saver is enabled.
"""
from pathlib import Path
p=Path(__file__).resolve().parents[2]/"kernel/drivers/cpufreq/cpu-boost.c"
s=p.read_text()

def replace(old,new,label):
    global s
    assert s.count(old)==1, f"Input contract changed at {label}"
    s=s.replace(old,new,1)

replace(
    """    if (!READ_ONCE(ay_screenoff_saver))
        return NOTIFY_DONE;

""",
    """    /* Always track panel state, including when the optional saver is
     * disabled at runtime. Otherwise a later UNBLANK can leave input
     * boosting locked out with ay_screen_on stuck false.
     */

""",
    "remove unsafe display-state early return",
)
replace(
    """    if (!READ_ONCE(ay_deepdoze_enabled) ||
        READ_ONCE(ay_screen_on))
""",
    """    if (!READ_ONCE(ay_deepdoze_enabled) ||
        !READ_ONCE(ay_screenoff_saver) ||
        READ_ONCE(ay_screen_on))
""",
    "stop disabled saver from activating deepdoze",
)
replace(
    """            if (READ_ONCE(ay_deepdoze_enabled))
                mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,
                                 msecs_to_jiffies(600000));
""",
    """            if (READ_ONCE(ay_screenoff_saver) &&
                READ_ONCE(ay_deepdoze_enabled))
                mod_delayed_work(cpu_boost_wq, &ay_deepdoze_timer,
                                 msecs_to_jiffies(600000));
""",
    "only arm timer when saver enabled",
)
assert s.count("WRITE_ONCE(ay_screen_on, true)") >= 1
assert s.count("WRITE_ONCE(ay_screen_on, false)") >= 1
assert s.count("msecs_to_jiffies(600000)") == 2
p.write_text(s)
print("V7.1.1: panel state always tracked; disabled saver cannot arm timer.")
