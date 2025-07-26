# PowerShell test script for DatePrinter
# Tests all months with varying day formats (single and double digit)

Write-Host "DatePrinter Monthly Test Script" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
Write-Host ""

# Test today's date first
Write-Host "Testing today's date..." -ForegroundColor Yellow
python date-printer.py
Start-Sleep -Seconds 2

# Test dates for each month
$testDates = @(
    @{Month="January"; Date="2024-01-05"; Day="5"},
    @{Month="January"; Date="2024-01-15"; Day="15"},
    @{Month="February"; Date="2024-02-08"; Day="8"},
    @{Month="February"; Date="2024-02-28"; Day="28"},
    @{Month="March"; Date="2024-03-03"; Day="3"},
    @{Month="March"; Date="2024-03-31"; Day="31"},
    @{Month="April"; Date="2024-04-01"; Day="1"},
    @{Month="April"; Date="2024-04-30"; Day="30"},
    @{Month="May"; Date="2024-05-09"; Day="9"},
    @{Month="May"; Date="2024-05-25"; Day="25"},
    @{Month="June"; Date="2024-06-07"; Day="7"},
    @{Month="June"; Date="2024-06-20"; Day="20"},
    @{Month="July"; Date="2024-07-04"; Day="4"},
    @{Month="July"; Date="2024-07-17"; Day="17"},
    @{Month="August"; Date="2024-08-02"; Day="2"},
    @{Month="August"; Date="2024-08-22"; Day="22"},
    @{Month="September"; Date="2024-09-06"; Day="6"},
    @{Month="September"; Date="2024-09-19"; Day="19"},
    @{Month="October"; Date="2024-10-08"; Day="8"},
    @{Month="October"; Date="2024-10-31"; Day="31"},
    @{Month="November"; Date="2024-11-01"; Day="1"},
    @{Month="November"; Date="2024-11-24"; Day="24"},
    @{Month="December"; Date="2024-12-09"; Day="9"},
    @{Month="December"; Date="2024-12-25"; Day="25"}
)

foreach ($test in $testDates) {
    Write-Host ""
    Write-Host "Testing $($test.Month) - Day $($test.Day) (Date: $($test.Date))" -ForegroundColor Green
    python date-printer.py -d $test.Date
    
    # Pause between prints to avoid overwhelming the printer
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "Test completed!" -ForegroundColor Cyan
Write-Host "Total labels printed: $($testDates.Count + 1)" -ForegroundColor Cyan