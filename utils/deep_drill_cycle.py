def _fmt(value):
    return f"{float(value):.3f}"


retract_or_insert_rpm = 100.0  # rpm, speed for retracting or inserting the tool
retract_or_insert_feed = 1000.0  # mm/min, feed for retracting or inserting the tool


def generate_deep_hole_cycle(
    start_z,
    final_depth,
    tool_diameter,
    max_peck,
    retract,
    safe_height,
    spindle_rpm,
    feed,
    dwell_time=0.0,
    coolant_code="M8",
):
    """Generate a deep-hole drilling sequence using only G0/G1/G4 motion blocks.

    The cycle follows the requested pattern:
    1. Rapid positioning 2 mm above the hole top.
    2. Initial plunge to 1.5 * tool diameter.
    3. Coolant on and optional dwell.
    4. Peck-drilling with retraction kept inside the hole between passes.
    """
    lines = []
    first_plunge_depth = max(start_z - (1.5 * float(tool_diameter)), float(final_depth))
    lines.append("M9")
    lines.append(f"; {first_plunge_depth:.3f} = {start_z:.3f} - (1.5 * {float(tool_diameter):.3f})")
    lines.append(f"S{int(retract_or_insert_rpm)} M3")
    lines.append(f"G1 Z{_fmt(first_plunge_depth)} F{float(retract_or_insert_feed):.1f}")
    lines.append(f"S{int(spindle_rpm)} M3")
    lines.append(coolant_code)
    if float(dwell_time) > 0:
        lines.append(f"G4 P{float(dwell_time):.3f}")

    current_depth = first_plunge_depth
    i = 0
    while current_depth > float(final_depth):
        i = i + 1
        if i > 20:
            lines.append(f"; Warning: Exceeded 20 pecks, current_depth={current_depth}, final_depth={final_depth}, max_peck={max_peck}, retract={retract}")
            return lines  # Prevent infinite loop in case of misconfiguration
        next_depth = max(float(final_depth), current_depth - float(max_peck))
        lines.append(f"G1 Z{_fmt(next_depth)} F{float(feed):.1f} ; Peck drilling")
        if next_depth <= float(final_depth):
            break
        current_depth = next_depth
        retract_depth = current_depth + float(retract)
        if retract_depth > next_depth:
            lines.append(f"G1 Z{_fmt(retract_depth)} F{float(retract_or_insert_feed):.1f} ; Retract")

    lines.append("M9")
    lines.append(f"G1 Z{_fmt(safe_height)} F{float(retract_or_insert_feed):.1f} ; Move to safe height")
    return lines
