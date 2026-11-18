from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

project = Path(__file__).resolve().parents[1]
build, output = project / "Build", project / "Upwell-Windows.zip"
assert (build/"Upwell.exe").is_file() and (build/"Upwell_Data/sharedassets0.assets").is_file()
instructions = """UPWELL — CAR 07

Extract the entire archive, then open Upwell.exe.

The guided passage presents 58 hours and 43 minutes aboard in six minutes.
The multiplier beside the onboard clock shows the current pace. Open M and
choose Real ship time (1×) to ride a stretch second by second. Hands and
loose objects move in real time in either mode. Harbor optics follows the
working port. The cable tender shortcut looks down the neighboring guideway.
Stargazing window dims the forward saloon during orbital night. Guided
spends 20 seconds at 1× while your eyes adjust. At the dock, choose
Valley gallery to look inside the rotating settlement.

Move with WASD or the arrow keys and look with the mouse. E or a click
operates a fitting. Drag a handle to move it, or press E at its grip.
F inspects the object in front of you. Tab selects a pocket item and I
brings it into the cabin light. Q operates its hardware, R turns it over,
and E stows it. G lets go. Drag and release to impart motion, or press E
to catch a loose object. F1 opens passenger controls. F2 opens Graphics.
Change anti-aliasing, cast shadows, atmosphere detail or cabin contact shading
there. Preferences are saved locally. Defaults restores this device’s settings.

The six-minute ascent is automatic. The three-detent selector on the
console switches exterior cameras. V cycles the passenger window seats
and full-view optics. 6 looks straight down through the glazed deck.
M opens the thirteen passage moments. [ and ] move between them. N and P
move to the next or previous route stage.
In microgravity, Space pushes off the deck or ceiling. W/S push along
your sightline, A/D push sideways and X moves deckward. Release the keys
to coast. H braces within reach of a surface. G releases an item in hand.
Use the suggested-view checkbox to choose whether the camera follows.
Shift with either bracket moves between route stages.
C opens the colony telescope. At soft capture it hands off to the Aster hub's optical head.

7 inspects the mechanical accelerometer. 8 inspects the galley capillary
cell. Q operates the test plunger or primer, and E returns you to the aisle.
Hold and drag the berth quilt, screen hem or an exposed service cable to move
it. Q gives a fitting a short local tug. 9 faces the berth screen's handle.
Drag its black grip horizontally and release to park the screen partway.

Unlock the service hatch with the crew key from the berth drawer. At the
aft bulkhead, hold the orange proof lever to fracture the ceramic coupon.
F inspects the guarded cell. In this view, hold Q to load the lever, release
it, then press R to exchange the sealed magazine. B focuses the bench
once its hatch has been unlocked.

K takes a photograph from your current cabin or optical view. J opens your
six-frame local journal. Each frame records the passage time, altitude and
signed cabin load. M opens the passage timetable. Select Crest the cloud deck
to start inside the last bank at 1:36.

At 1:12, press O for the shaded side window. Look for Car 07's shadow on
the nearby cloud and the faint ring of color around it. Press K to keep
a photograph with its altitude and cabin load.

Try bringing the galley flask to the dock. Release it, push off to catch it
and carry it back to the counter in the crew sleeper. T seats it in its
keeper when you are within arm's reach. Hold Q on the flask to open the
drinking valve and release it to close the port.
"""
with ZipFile(output.with_suffix(".tmp"), "w", ZIP_DEFLATED, compresslevel=6) as archive:
    for file in sorted(build.rglob("*")):
        if file.is_file() and not any("DoNotShip" in x for x in file.parts):
            archive.write(file, file.relative_to(build))
    archive.writestr("How to play.txt", instructions)
    credits=project/"Assets/Upwell/Environment/Earth-data-credits.txt"
    if credits.is_file():archive.write(credits,"Earth data credits.txt")
    archive.write(project.parent/"web/assets/fonts/Geist-license.txt","Licenses/Geist.txt")
output.with_suffix(".tmp").replace(output)
with ZipFile(output) as archive:
    assert archive.testzip() is None
print(f"{output} · {output.stat().st_size/1024/1024:.1f} MiB")
