import math
import sys
from tabulate import tabulate


SHACKLES = [
    {"size": "3/4", "wll": 4.75, "pin": 22.61, "jaw": 31.75},
    {"size": "7/8", "wll": 6.50, "pin": 25.91, "jaw": 36.58},
    {"size": "1", "wll": 8.50, "pin": 29.21, "jaw": 42.93},
    {"size": "1-1/8", "wll": 9.50, "pin": 31.75, "jaw": 45.97},
    {"size": "1-1/4", "wll": 12.00, "pin": 35.56, "jaw": 51.56},
    {"size": "1-3/8", "wll": 13.50, "pin": 38.86, "jaw": 57.15},
]


CHECKS = {
    "3-45": ("BTH 3-45", "increase outer radius R or plate thickness t"),
    "3-49": ("BTH 3-49", "increase outer radius R or plate thickness t"),
    "3-50": ("BTH 3-50", "increase outer radius R or plate thickness t"),
    "3-53": ("BTH 3-53", "add or thicken cheek plates tc, or increase plate thickness t"),
    "3-28": ("BTH 3-28", "increase base length L or plate thickness t"),
    "3-35": ("BTH 3-35", "increase base length L, increase thickness t, or reduce height y"),
    "3-37": ("BTH 3-37", "increase base length L, increase thickness t, or reduce height y"),
    "3-55": ("BTH 3-55", "larger weld leg or longer weld"),
    "J2.4": ("AISC J2.4", "increase weld leg to at least the minimum required size"),
    "G1": ("DNV 16.9.5.1", "increase outer radius R to at least hole diameter DH"),
    "G2": ("DNV 16.9.5.3", "increase plate or cheek thickness so total thickness >= 0.75 x jaw"),
    "G3": ("DNV 16.9.5.4", "reduce cheek plate thickness tc so tc <= main plate thickness t"),
    "G4": ("DNV 16.9.5.2", "adjust hole diameter DH to stay within pin + max(2 mm, 3%) and pin + 6 mm"),
    "G5": ("DNV P.2.4.2", "reduce out-of-plane sling angle or use a tighter pin-to-hole fit (Dp >= 0.94 DH)"),
    "G6": ("DNV shackle fit", "use a shackle with a wider jaw or reduce total plate thickness"),
}

#-----------------------------------------------------------------
# Asks for the inputs, runs the checks, prints the report
#-----------------------------------------------------------------
def main():
    print("=== LugCheck: Lifting-Lug Structural Check ===")
    lug_axis = get_axis(
        "Lug points from weld to hole (+Y, +X, -X, +Z, -Z): ",
        ["+Y", "+X", "-X", "+Z", "-Z"],
    )

    if lug_axis[1] == "X":
        thickness_choices = ["Y", "Z"]
        thickness_prompt = "Plate thickness is along axis (Y / Z): "
    elif lug_axis[1] == "Z":
        thickness_choices = ["X", "Y"]
        thickness_prompt = "Plate thickness is along axis (X / Y): "
    else:
        thickness_choices = ["X", "Z"]
        thickness_prompt = "Plate thickness is along axis (X / Z): "

    thickness = get_axis(thickness_prompt, thickness_choices)

    t_kn = get_number("Static sling force at the lug (kN): ", None, 0.1)
    dx = get_number("Hook position dX (mm) [0]: ", 0.0, None)
    dy = get_number("Hook position dY (height above hole, mm): ", None, 1.0)
    dz = get_number("Hook position dZ (mm) [0]: ", 0.0, None)

    t = get_number("Main plate thickness t (mm): ", None, 1.0)
    r = get_number("Outer radius R (mm): ", None, 1.0)
    dh = get_number("Hole diameter DH (mm): ", None, 1.0)
    y = get_number("Weld line to hole centre y (mm): ", None, 1.0)
    base = get_number("Lug base / weld length L (mm): ", None, 1.0)
    tc = get_number("Cheek plate thickness each side (mm) [0]: ", 0.0, 0.0)
    w = get_number("Fillet weld leg w (mm): ", None, 3.0)
    tb = get_number("Thinner part joined by weld tb (mm): ", None, 1.0)

    fy = get_number("Plate yield strength Fy (MPa) [275]: ", 275.0, 1.0)
    fu = get_number("Plate tensile strength Fu (MPa) [430]: ", 430.0, 1.0)
    exx = get_number("Electrode strength Exx (MPa) [480]: ", 480.0, 1.0)
    nd = get_number("BTH design factor Nd [2]: ", 2.0, 2.0)

    daf = get_number("Dynamic amplification factor DAF [1.10]: ", 1.10, 1.0)
    skl = get_number("Skew load factor SKL [1.00]: ", 1.00, 1.0)
    gamma_c = get_number("Consequence factor gamma_c [1.30]: ", 1.30, 1.0)

    lug = {
        "t": t,
        "r": r,
        "dh": dh,
        "y": y,
        "l": base,
        "tc": tc,
        "w": w,
        "tb": tb,
        "fy": fy,
        "fu": fu,
        "exx": exx,
    }

    f_lug, f_shackle = design_loads(t_kn * 1000.0, daf, skl, gamma_c)
    pull, along, out, angle = resolve_force(f_lug, dx, dy, dz, lug_axis, thickness)

    t_total = t + 2.0 * tc
    shackle = select_shackle(f_shackle, dh, t_total)
    if shackle is None:
        sys.exit("No suitable Crosby G-2130 shackle found in catalogue for this load/geometry.")

    dp = shackle["pin"]
    fip = math.sqrt(pull ** 2 + along ** 2)

    pin_ratios = pin_plate_check(fip, lug, dp, nd)
    plate_ratios = plate_check(pull, along, out, lug, dp, nd)
    weld_ratio, min_leg = weld_check(pull, along, out, lug, dp, nd)

    needed_leg = None
    if weld_ratio > 1.0 or w < min_leg:
        needed_leg = weld_leg_needed(pull, along, out, lug, dp, nd)

    fn_ratio = out / f_lug
    dnv_results = dnv_checks(lug, shackle, fn_ratio)

    print_report(
        lug_axis,
        thickness,
        f_lug,
        f_shackle,
        pull,
        along,
        out,
        angle,
        shackle,
        lug,
        pin_ratios,
        plate_ratios,
        weld_ratio,
        min_leg,
        needed_leg,
        dnv_results,
    )

#-----------------------------------------------------------------
# Keeps asking until a valid number is typed; Enter gives the default
#-----------------------------------------------------------------
def get_number(prompt, default, minimum):
    while True:
        text = input(prompt).strip()
        if text == "" and default is not None:
            return float(default)
        try:
            number = float(text)
        except ValueError:
            print("Invalid number. Please try again.")
            continue

        if minimum is not None and number < minimum:
            print(f"Value must be at least {minimum}.")
            continue
        return number

#-----------------------------------------------------------------
# The DNV load chain; returns the lug load and the shackle load in N
#-----------------------------------------------------------------
def design_loads(t_static, daf, skl, gamma_c):
    f_lug = t_static * daf * skl * gamma_c
    f_shackle = t_static * skl
    return f_lug, f_shackle

#-----------------------------------------------------------------
# Keeps asking until one of the allowed axis codes is typed
#-----------------------------------------------------------------
def get_axis(prompt, choices):
    while True:
        answer = input(prompt).strip().upper()
        for choice in choices:
            if answer == choice.upper():
                return answer
        print(f"Invalid choice. Please enter one of: {', '.join(choices)}")

#-----------------------------------------------------------------
# Splits the force into pull-out, along-weld and out-of-plane; returns them with the sling angle
#-----------------------------------------------------------------
def resolve_force(f, dx, dy, dz, points, thickness, p_lat=0.03):
    length = math.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
    forces = {
        "X": f * dx / length,
        "Y": f * dy / length,
        "Z": f * dz / length,
    }

    points_axis = points[1]
    if points[0] == "+":
        pull = forces[points_axis]
    else:
        pull = -forces[points_axis]

    if points_axis != "X" and thickness != "X":
        weld_axis = "X"
    elif points_axis != "Y" and thickness != "Y":
        weld_axis = "Y"
    else:
        weld_axis = "Z"

    along = abs(forces[weld_axis])
    out = abs(forces[thickness]) + p_lat * f

    horizontal = math.sqrt(dx ** 2 + dz ** 2)
    angle = math.degrees(math.atan2(dy, horizontal))
    return pull, along, out, angle

#-----------------------------------------------------------------
# The smallest shackle passing WLL, G4 and G6, or None
#-----------------------------------------------------------------
def select_shackle(f_shackle, dh, t_total):
    for row in SHACKLES:
        wll_n = row["wll"] * 9806.65
        min_dh = row["pin"] + max(2.0, 0.03 * row["pin"])
        max_dh = row["pin"] + 6.0
        if wll_n >= f_shackle and min_dh <= dh <= max_dh and row["jaw"] >= t_total + 3.0:
            return row
    return None

#-----------------------------------------------------------------
# BTH-1 Eqs. 3-45, 3-49, 3-50, 3-53; returns the ratios
#-----------------------------------------------------------------
def pin_plate_check(fip, lug, dp, nd):
    t = lug["t"]
    r = lug["r"]
    dh = lug["dh"]
    tc = lug["tc"]
    fy = lug["fy"]
    fu = lug["fu"]

    d_ratio = dp / dh
    if d_ratio > 0.90:
        cr = 1.0
    else:
        cr = 1.0 - 0.275 * math.sqrt(1.0 - d_ratio ** 2)

    be = r - dh / 2.0
    beff = min(4.0 * t, be, 0.6 * be * (fu / fy) * math.sqrt(dh / be))

    pt = cr * fu / (1.20 * nd) * 2.0 * t * beff
    pb = cr * fu / (1.20 * nd) * (1.13 * be + 0.92 * be / (1.0 + be / dh)) * t
    phi = math.radians(55.0 * dp / dh)
    pv = 0.70 * fu / (1.20 * nd) * 2.0 * (be + (dp / 2.0) * (1.0 - math.cos(phi))) * t
    pp = 1.25 * fy / nd * dp * (t + 2.0 * tc)

    return {
        "3-45": fip / pt,
        "3-49": fip / pb,
        "3-50": fip / pv,
        "3-53": fip / pp,
    }

#-----------------------------------------------------------------
# BTH-1 Eqs. 3-20/22/24; returns the allowable stress in MPa
#-----------------------------------------------------------------
def strong_axis_allowable(y, base, t, fy, nd):
    e_mod = 200000.0
    lam = y * base / (t ** 2)
    c_ltb = min(1.0, 2.42 * base / y)
    f_max = 1.25 * fy / nd

    if lam <= 0.08 * e_mod / fy:
        f_allow = f_max
    elif lam <= 1.9 * e_mod / fy:
        f_allow = c_ltb * (1.52 - 0.274 * lam * fy / e_mod) * fy / nd
    else:
        f_allow = c_ltb * 1.9 * e_mod / (nd * lam)

    if f_allow > f_max:
        return f_max
    return f_allow

#-----------------------------------------------------------------
# The in-plane moment, out-of-plane moment and torque at the weld (N·mm)
#-----------------------------------------------------------------
def weld_line_moments(fa, fb, fn, y, dh, dp):
    c = (dh - dp) / 2.0
    m_in = fb * (y + c) + abs(fa) * c
    m_out = fn * (y + dh / 2.0)
    torque = fn * (dh / 2.0)
    return m_in, m_out, torque

#-----------------------------------------------------------------
# BTH-1 Eqs. 3-28, 3-35, 3-37 at the weld line; returns the ratios
#-----------------------------------------------------------------
def plate_check(fa, fb, fn, lug, dp, nd):
    t = lug["t"]
    base = lug["l"]
    y = lug["y"]
    dh = lug["dh"]
    fy = lug["fy"]

    m_in, m_out, torque = weld_line_moments(fa, fb, fn, y, dh, dp)

    f_a = abs(fa) / (base * t)
    f_in = m_in / (t * (base ** 2) / 6.0)
    f_out = m_out / (base * (t ** 2) / 6.0)
    f_v = math.sqrt(fb ** 2 + fn ** 2) / (base * t) + 3.0 * torque / (base * (t ** 2))

    f_strong = strong_axis_allowable(y, base, t, fy, nd)

    r_328 = f_v / (fy / (nd * math.sqrt(3.0)))
    r_335 = f_a / (fy / nd) + f_in / f_strong + f_out / (1.25 * fy / nd)
    r_337 = math.sqrt((f_a + f_in + f_out) ** 2 + 3.0 * (f_v ** 2)) / (fy / nd)

    return {
        "3-28": r_328,
        "3-35": r_335,
        "3-37": r_337,
    }

#-----------------------------------------------------------------
# BTH-1 Eq. 3-55 weld ratio and the AISC J2.4 minimum leg
#-----------------------------------------------------------------
def weld_check(fa, fb, fn, lug, dp, nd):
    t = lug["t"]
    base = lug["l"]
    y = lug["y"]
    dh = lug["dh"]
    w = lug["w"]
    tb = lug["tb"]
    exx = lug["exx"]

    m_in, m_out, torque = weld_line_moments(fa, fb, fn, y, dh, dp)

    throat = 0.707 * w
    area = 2.0 * base * throat
    j_polar = 2.0 * throat * ((base ** 3) / 12.0 + base * ((t / 2.0) ** 2))

    f_norm = (
        abs(fa) / area
        + m_in / (2.0 * throat * (base ** 2) / 6.0)
        + m_out / (t * base * throat)
    )
    f_sb = fb / area + torque * (t / 2.0) / j_polar
    f_sn = fn / area + torque * (base / 2.0) / j_polar

    f_res = math.sqrt(f_norm ** 2 + f_sb ** 2 + f_sn ** 2)
    f_allow = 0.60 * exx / (1.20 * nd)
    ratio = f_res / f_allow

    if tb <= 6.0:
        min_leg = 3
    elif tb <= 13.0:
        min_leg = 5
    elif tb <= 19.0:
        min_leg = 6
    else:
        min_leg = 8

    return ratio, min_leg

#-----------------------------------------------------------------
# The smallest leg from 3 to 30 mm that passes, or None
#-----------------------------------------------------------------
def weld_leg_needed(fa, fb, fn, lug, dp, nd):
    trial_lug = lug.copy()
    for leg in range(3, 31):
        trial_lug["w"] = float(leg)
        ratio, min_leg = weld_check(fa, fb, fn, trial_lug, dp, nd)
        if ratio <= 1.0 and leg >= min_leg:
            return leg
    return None

#-----------------------------------------------------------------
# DNV G1–G6; returns PASS, FAIL or WARNING for each rule
#-----------------------------------------------------------------
def dnv_checks(lug, shackle, fn_ratio):
    t = lug["t"]
    tc = lug["tc"]
    r = lug["r"]
    dh = lug["dh"]
    t_total = t + 2.0 * tc

    if r >= dh:
        g1 = "PASS"
    else:
        g1 = "FAIL"

    if t_total >= 0.75 * shackle["jaw"]:
        g2 = "PASS"
    else:
        g2 = "FAIL"

    if tc <= t:
        g3 = "PASS"
    else:
        g3 = "FAIL"

    min_dh = shackle["pin"] + max(2.0, 0.03 * shackle["pin"])
    max_dh = shackle["pin"] + 6.0
    if min_dh <= dh <= max_dh:
        g4 = "PASS"
    else:
        g4 = "WARNING"

    if fn_ratio > 0.10 and shackle["pin"] < 0.94 * dh:
        g5 = "FAIL"
    else:
        g5 = "PASS"

    if shackle["jaw"] >= t_total + 3.0:
        g6 = "PASS"
    else:
        g6 = "FAIL"

    return {
        "G1": g1,
        "G2": g2,
        "G3": g3,
        "G4": g4,
        "G5": g5,
        "G6": g6,
    }

#-----------------------------------------------------------------
# Prints the three tables, the OVERALL result and the suggestions
#-----------------------------------------------------------------
def print_report(
    points,
    thickness,
    f_lug,
    f_shackle,
    pull,
    along,
    out,
    angle,
    shackle,
    lug,
    pin_ratios,
    plate_ratios,
    weld_ratio,
    min_leg,
    needed_leg,
    dnv_results,
):
    points_axis = points[1]
    if points_axis != "X" and thickness != "X":
        weld_axis = "X"
    elif points_axis != "Y" and thickness != "Y":
        weld_axis = "Y"
    else:
        weld_axis = "Z"

    print()
    if pull < 0:
        print("Note: pull-out force points toward the weld; using its magnitude conservatively.")

    print(
        f"Forces: pull-out F{points_axis} {abs(pull) / 1000.0:.2f} kN | "
        f"along weld F{weld_axis} {along / 1000.0:.2f} kN | "
        f"out-of-plane F{thickness} {out / 1000.0:.2f} kN (incl. 3% lateral)"
    )
    print()
    print(
        f"Design load {f_lug / 1000.0:.2f} kN | "
        f"shackle load {f_shackle / 1000.0:.2f} kN | "
        f"sling angle {angle:.1f} deg | "
        f"out-of-plane {(out / f_lug) * 100.0:.1f}%"
    )
    print(
        f"Shackle: Crosby G-2130 {shackle['size']} in "
        f"(WLL {shackle['wll']} t, pin {shackle['pin']} mm, jaw {shackle['jaw']} mm)"
    )

    bth_items = [
        ("Pin tension", "3-45", pin_ratios["3-45"]),
        ("Single-plane fracture", "3-49", pin_ratios["3-49"]),
        ("Double-plane shear", "3-50", pin_ratios["3-50"]),
        ("Bearing", "3-53", pin_ratios["3-53"]),
        ("Shear at weld line", "3-28", plate_ratios["3-28"]),
        ("Combined stress", "3-35", plate_ratios["3-35"]),
        ("Von Mises", "3-37", plate_ratios["3-37"]),
        ("Weld stress", "3-55", weld_ratio),
    ]

    failed_items = []
    bth_rows = []
    for label, key, ratio in bth_items:
        if ratio <= 1.0:
            status = "PASS"
        else:
            status = "FAIL"
            failed_items.append((label, key))
        bth_rows.append([label, CHECKS[key][0], f"{ratio:.3f}", status])

    print("\nASME BTH-1-2017")
    print(tabulate(bth_rows, headers=["Check", "Reference", "Ratio", "Status"], tablefmt="simple", disable_numparse=True))

    if lug["w"] >= min_leg:
        aisc_status = "PASS"
    else:
        aisc_status = "FAIL"
        failed_items.append(("Minimum weld size", "J2.4"))

    print("\nAISC 360-16")
    print(f"Minimum weld size (J2.4): {int(lug['w'])} mm vs {min_leg} mm  {aisc_status}")

    dnv_labels = [
        ("G1 radius", "G1"),
        ("G2 thickness", "G2"),
        ("G3 cheeks", "G3"),
        ("G4 hole clearance", "G4"),
        ("G5 out-of-plane", "G5"),
        ("G6 jaw fit", "G6"),
    ]
    dnv_rows = []
    for label, key in dnv_labels:
        status = dnv_results[key]
        dnv_rows.append([label, CHECKS[key][0], status])
        if status == "FAIL":
            failed_items.append((label, key))

    print("\nDNV-ST-N001")
    print(tabulate(dnv_rows, headers=["Rule", "Reference", "Status"], tablefmt="simple"))

    if lug["tc"] > 0:
        print("Note: cheek-plate welds are not checked.")

    if len(failed_items) == 0:
        print("\nOVERALL: PASS")
    else:
        print("\nOVERALL: FAIL")
        for label, key in failed_items:
            ref, suggestion = CHECKS[key]
            print(f"  - {label} ({ref}): {suggestion}")

    if weld_ratio > 1.0 or aisc_status == "FAIL":
        if needed_leg is not None:
            print(f"  Smallest weld leg that passes: {needed_leg} mm")
        else:
            print("  Smallest weld leg that passes: > 30 mm (increase weld length L)")

if __name__ == "__main__":
    main()
