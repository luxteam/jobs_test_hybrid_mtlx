set PATH=c:\python39\;c:\python39\scripts\;%PATH%
set FILE_FILTER=%1
set TESTS_FILTER="%2"
set UPDATE_REFS=%3

if not defined UPDATE_REFS set UPDATE_REFS="No"

python -m pip install -r ../jobs_launcher/install/requirements.txt

python ..\jobs_launcher\executeTests.py --test_filter %TESTS_FILTER% --file_filter %FILE_FILTER% --tests_root ..\jobs --work_root ..\Work\Results --work_dir HybMTLX --cmd_variables Tool "..\tool\trace.exe" ResPath "C:\TestResources\hybrid_mtlx_autotests_assets" UpdateRefs %UPDATE_REFS%