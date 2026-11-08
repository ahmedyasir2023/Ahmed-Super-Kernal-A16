#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
CHECKS=[
("kernel/kernel/sched/cpufreq_schedutil.c","AY_V10_4_FAST_UP_CAP_US 250"),
("kernel/kernel/sched/cpufreq_schedutil.c","ay_v10_4_schedutil_fast_up"),
("kernel/kernel/sched/cpufreq_schedutil.c","sugov_effective_up_rate_delay_ns"),
("kernel/drivers/cpufreq/cpu-boost.c","ay_v10_policy_dedup"),
("kernel/drivers/cpufreq/cpu-boost.c","ay_v10_boost_fastpath"),
("kernel/kernel/sched/fair.c","enqueue_task_fair"),
]
for rel,token in CHECKS: assert token in (ROOT/rel).read_text(errors="replace"), f"{rel}: missing {token}"
for rel,token in [("kernel/kernel/sched/cpufreq_schedutil.c","thermal_disable"),("kernel/drivers/cpufreq/cpu-boost.c","policy->max =")]:
    assert token not in (ROOT/rel).read_text(errors="replace"), f"Forbidden pattern {token}"
print("PASS: scheduler, WALT and bounded UI boost contracts.")
