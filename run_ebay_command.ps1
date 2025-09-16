# PowerShell script to run eBay commands with proper argument handling
# This handles special characters better than Command Prompt

param(
    [Parameter(Mandatory=$true)]
    [string]$Command,
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

if ($Arguments.Count -eq 0) {
    Write-Host "Usage: .\run_ebay_command.ps1 -Command <command> [arguments...]"
    Write-Host "Commands: search, seller, item, collect, process, top, copy, refresh"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host ".\run_ebay_command.ps1 -Command search -Arguments 'item with ^ and | characters'"
    Write-Host ".\run_ebay_command.ps1 -Command seller -Arguments 'username', 'query with | pipes'"
    exit 1
}

# Build the command line arguments array
$allArgs = @($Command) + $Arguments

# Run the Python script with properly escaped arguments
& python ebay_search_test.py @allArgs
