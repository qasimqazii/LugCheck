# LugCheck: Lifting-Lug Checks as per ASME BTH-1, AISC 360 and DNV-ST-N001
#### Video Demo:  https://youtu.be/Jal_pOpsMm8
#### Description:

At work, I routinely design and check steel lifting lugs for steel structures like skids, E-houses and platforms. Since different provisions are provided in the different design codes, like ASME BTH-1, AISC 360 and DNV-ST-N001, manual calculations become complex and repetitive. To automate this process, I built **LugCheck**. It is a clean, simple-to-understand command-line Python tool that performs the same lifting-lug verification and provides suggestions in case the lug fails any design check.

LugCheck checks one lifting lug at a time using global STAAD axes. `X-axis` is across the structure, `Y-axis` is vertical/up and `Z-axis` is along the structure. One of the best features of LugCheck is that it works for lugs mounted either on top of a beam flange (pointing `+Y`) or on the side of a beam web (pointing `+X`, `-X`, `+Z`, or `-Z`). You enter the hook position as `dX`, `dY`, `dZ` from the hole centre, and the program then computes the true sling unit vector. It splits the factored load into pull-out, along-weld, and out-of-plane forces (adding DNV's minimum 3% lateral load), and labels each force by its STAAD axis letter. If a sling pulls back toward the weld, LugCheck prints a note and conservatively uses the magnitude of the pull-out force. It then selects the smallest suitable Crosby G-2130 shackle from a built-in catalogue, runs all strength and geometry checks, prints the summary tables for `ASME BTH-1-2017`, `AISC 360-16`, and `DNV-ST-N001`. The program reports `OVERALL: PASS` or `OVERALL: FAIL` and finally lists code references and engineering suggestions for every failed item, including the smallest passing fillet weld leg size if the weld fails.

## How to run it

Install the required packages (`tabulate` and `pytest`) and run the main program or test suite from the project folder:

```bash
pip install -r requirements.txt
python project.py
pytest test_project.py
```

## Inputs

LugCheck prompts for all inputs interactively in SI units (`kN`, `mm`, `MPa`). Pressing `Enter` accepts a default value marked in [] where applicable:

* **Orientation:** Direction the lug points from weld to hole (`+Y`, `+X`, `-X`, `+Z`, `-Z`), followed by the axis along which the plate thickness runs.
* **Loading and hook geometry:** Unfactored static sling force at the lug (`kN`) and hook offsets `dX`, `dY`, and `dZ` in `mm` from the lug's hole centre.
* **Plate and weld sizes (`mm`):** Main plate thickness `t`, outer radius `R`, hole diameter `DH`, weld-to-hole height `y`, base/weld length `L`, cheek plate thickness each side `tc` (`0 mm` if none), fillet weld leg `w`, and thinner part joined `tb`.
* **Material and load factors:** Yield strength `Fy` (`MPa`), tensile strength `Fu` (`MPa`), weld electrode strength `Exx` (`MPa`), BTH design factor `Nd` (`2` for Category A, `3` for Category B), dynamic amplification factor `DAF` (`1.10`, DNV Table 16-1 onshore), skew load factor `SKL` (`1.00`), and consequence factor `gamma_c` (`1.30`).

## Checks and design basis

All structural checks use a single consistent ASME BTH-1-2017 allowable stress design basis (`Fy/Nd`, `1.25Fy/Nd`, `Fy/(Nd*sqrt(3))`, and `0.60Exx/(1.20Nd)`). Following DNV-ST-N001, the lug design load is `F_lug = T * DAF * SKL * gamma_c`, whereas the shackle selection load is `F_shackle = T * SKL` (per DNV 16.5.2.5). The shackle's WLL already includes the manufacturer's safety factor against breaking. So `DAF` and `gamma_c` are applied to the structure being designed (lug) only.

* **ASME BTH-1-2017 (8 checks):** Pin-hole tension (`3-45`), single-plane fracture (`3-49`), double-plane shear (`3-50`), bearing (`3-53`), weld-line shear (`3-28`), combined axial and biaxial bending (`3-35`, using strong-axis allowable stress from `3-20`/`3-22`/`3-24`), von Mises stress (`3-37`), and combined fillet weld group stress (`3-55`).
* **AISC 360-16:** Minimum fillet weld leg size per Table `J2.4` based on the thinner part joined (`tb`).
* **DNV-ST-N001 (6 rules):** Edge radius `G1` (`16.9.5.1`), total thickness vs. shackle jaw `G2` (`16.9.5.3`), cheek plate thickness `G3` (`16.9.5.4`), pin-hole clearance `G4` (`16.9.5.2`, reported as `WARNING` if outside `pin + max(2 mm, 3%)` to `pin + 6 mm`), out-of-plane pin fit `G5` (`P.2.4.2`), and shackle jaw fit `G6`.


## Files and design choices

* **`project.py` (~530 lines, 14 functions):** Contains `main()` plus 13 top-level functions (`get_number`, `design_loads`, `get_axis`, `resolve_force`, `select_shackle`, `pin_plate_check`, `strong_axis_allowable`, `weld_line_moments`, `plate_check`, `weld_check`, `weld_leg_needed`, `dnv_checks`, and `print_report`), along with two module-level tables: `SHACKLES` and `CHECKS`.
* **`test_project.py`:** Contains 9 `pytest` test functions (`test_design_loads`, `test_resolve_force`, `test_select_shackle`, `test_pin_plate_check`, `test_strong_axis_allowable`, `test_plate_check`, `test_weld_check`, `test_weld_leg_needed`, and `test_dnv_checks`) verified against independently calculated reference values.
* **`requirements.txt`:** Lists the two external dependencies, `tabulate` and `pytest`.

Key design choices include:
* **Smart orientation prompts:** Once the user enters which way the lug points (for example `+Y`), `main()` only offers the two perpendicular axes (`X / Z`) for the plate thickness, preventing invalid geometry before calculations even begin.
* **Strict input validation:** `get_number()` and `get_axis()` keep prompting until valid input is entered, so downstream functions never receive negative dimensions or invalid text.
* **Single `lug` dictionary:** Geometry and material properties travel between functions in one `dict` (`lug`) rather than passing 11 separate arguments to every check.
* **Built-in shackle and check tables:** Six Crosby G-2130 sizes (`3/4` to `1-3/8 in`, with imperial pin and jaw dimensions converted at `25.4 mm/in`) are stored in `SHACKLES` so there is no external CSV file to manage. If no shackle satisfies WLL, pin clearance, and jaw width, the program exits cleanly with a clear message. Similarly, `CHECKS` maps every equation key (`3-45` through `G6`) to its code reference and corrective suggestion.
* **Plain loops and `if/else` logic:** Written deliberately with straightforward loops and conditionals so every engineering formula is transparent and easy to audit by hand. `weld_leg_needed()` loops through weld legs from `3` to `30 mm` and tells the user to lengthen the weld if even `30 mm` is insufficient.

## Limitations

LugCheck evaluates one lifting lug at a time and assumes the lug plate and weld line align with the global `X`, `Y`, `Z` axes, the pin hole is centred over the weld length `L`, and bearing is Service Class 0. `Y` must be the vertical axis (the STAAD default). The lateral load is fixed at 3%. Cheek-plate fillet welds and the supporting beam flange or web are not checked. This tool is intended for preliminary engineering checks and does not replace a stamped lifting design approval.

## How I built it
1. I developed an Excel-based tool myself to design the lifting lugs. This served as the basis of my Python code.
2. I planned how to convert that Excel-tool to a Python project. I took an AI assistant (Claude)'s help to finalize the project's scope and organize the functions in my code.
3. I wrote all of the project.py and test_project.py.
4. I validated the engineering edge-cases through the expected test values form my initial excel-sheet. I also took AI assistant's help to develop these edge-cases.
5. I ran the code on CS50 codespace and used CS50 Duck where i got stuck.
6. After the code passed all the tests, i wrote the README file, made LugCheck's video and posted on youtube. The link is in the header.

## References

* ASME BTH-1-2017: *Design of Below-the-Hook Lifting Devices*
* AISC 360-16: *Specification for Structural Steel Buildings*
* DNV-ST-N001: *Marine Operations and Marine Warranty*
* Crosby Group G-2130 Bolt-Type Anchor Shackle Catalogue
* `tabulate` and `pytest` Python libraries