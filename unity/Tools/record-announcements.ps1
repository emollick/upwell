$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$output = Join-Path (Split-Path $PSScriptRoot -Parent) 'Assets/Upwell/Audio'
$lines = @(
    'Anchor control to Car Seven. Boarding bridge locked. Stand by while we release the guide arms.',
    'Car Seven has cleared the tower. All six guide drives are engaged.',
    'We are entering marine cloud. The exterior optical feed may briefly lose sight of the sea.',
    'Cloud tops below. The guide rollers are holding their nominal temperature.',
    'Stratosphere. The cabin is holding one atmosphere.',
    'Passing one hundred kilometres. The blue rim below the window is the atmosphere.',
    'Earth limb sector. The observation optics are following the horizon.',
    'High orbit. Anchor control is handing us over to Aster Reach.',
    'Aster control has acquired the carriage. Automatic terminal braking is active.',
    'Inside the receiving cradle. Keep the hatch shut until pressure matching completes.',
    'Carriage at rest. Set the docking handwheel to seat the terminal clamp.'
)
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.Rate = -1
    for ($index = 0; $index -lt $lines.Length; $index++) {
        $synth.SetOutputToWaveFile((Join-Path $output ("Dispatch" + $index + ".wav")))
        $synth.Speak($lines[$index])
        $synth.SetOutputToNull()
    }
} finally {$synth.Dispose()}
