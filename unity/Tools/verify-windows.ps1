param([switch]$InputOnly)
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
$output=Join-Path $project 'Verification'
New-Item -Path $output -ItemType Directory -Force | Out-Null
New-Item -Path (Join-Path $output 'graphics') -ItemType Directory -Force | Out-Null
$runs=if($InputOnly){@('native-input','graphics-reload')}else{@('native','native-input','graphics-reload','software')}
foreach($run in $runs){
    $inputFlag=if($run -eq 'native-input'){'-verify-native-input'}elseif($run -eq 'graphics-reload'){'-verify-graphics-reload'}else{''}
    $name=if($run -eq 'native-input'){'native-input.log'}elseif($run -eq 'graphics-reload'){'graphics/native-persistence.log'}else{'player.log'}
    $playerArgs=@('-force-d3d11','-screen-fullscreen','0','-screen-width','1440','-screen-height','900','-verify-upwell',$output,'-logFile',(Join-Path $output $name))
    if($inputFlag){$playerArgs+=$inputFlag}
    if($run -eq 'software'){$playerArgs=@('-force-d3d11','-force-driver-type-warp','-screen-fullscreen','0','-screen-width','448','-screen-height','280','-verify-upwell',$output,'-verify-software-graphics','-logFile',(Join-Path $output 'graphics/native-software.log'))}
    python (Join-Path $PSScriptRoot 'isolated-windows-player.py') (Join-Path $project 'Build/Upwell.exe') @playerArgs
    if($LASTEXITCODE -ne 0){throw "Native $run verification exited with code $LASTEXITCODE. See $output."}
}
