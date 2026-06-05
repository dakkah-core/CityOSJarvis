$env:TMP = 'C:\Dakkah-CityOS\CityOSJarvis\.tmp\pytest'
$env:TEMP = 'C:\Dakkah-CityOS\CityOSJarvis\.tmp\pytest'
uv run pytest --tb=short -q
exit $LASTEXITCODE
