# PII Discovery Report

## Summary
- Total files discovered: 3321
- Files processed: 3280
- Files with personal data: 962
- Errors: 11
- Warnings: 1012
- Unsupported files: 30
- Total processing time, sec: 768.3496

## Distribution by UZ
- NO_PD: 2359
- UZ-1: 377
- UZ-2: 175
- UZ-3: 54
- UZ-4: 356

## Top Categories
- phone: 125523
- email: 112979
- address: 62251
- inn: 35507
- bank_card: 32604
- passport_rf: 25420
- fio: 10359
- snils: 1663
- special_health: 531
- birth_date: 181

## Top Risk Files
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Логистика\logistics.csv` | UZ-1 | volume=large | categories=phone, special_health
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\дочерние предприятия\Billing\full\logistics.csv` | UZ-1 | volume=large | categories=phone, special_health
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\Otchet%202016.pdf` | UZ-1 | volume=large | categories=bank_card, phone, special_religion, special_health, fio, email, address
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\samoobsled_2024.pdf` | UZ-1 | volume=large | categories=phone, bank_card, special_health, fio, address
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\sostav_gr.xls` | UZ-1 | volume=large | categories=email, phone, fio, snils, special_health, inn
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\%D0%9F%D1%83%D0%B1%D0%BB%D0%B8%D1%87%D0%BD%D1%8B%D0%B9_%D0%BE%D1%82%D1%87%D1%91%D1%82_%D0%A2%D0%9A_%D0%AE%D0%A4%D0%A3_2024.pdf` | UZ-1 | volume=medium | categories=phone, bank_card, special_health, fio
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\%D0%9F%D1%83%D0%B1%D0%BB%D0%B8%D1%87%D0%BD%D1%8B%D0%B9%20%D0%BE%D1%82%D1%87%D1%91%D1%82%20%D0%A2%D0%9A%20%D0%AE%D0%A4%D0%A3.pdf` | UZ-1 | volume=medium | categories=phone, bank_card, special_health, fio
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\Реестр экскурсоводов 2024_ 02.12.2024.pdf` | UZ-1 | volume=medium | categories=email, phone, snils, fio, special_religion, inn
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\%D0%9F%D1%83%D0%B1%D0%BB%D0%B8%D1%87%D0%BD%D1%8B%D0%B9%20%D0%BE%D1%82%D1%87%D1%91%D1%82%202021.pdf` | UZ-1 | volume=medium | categories=phone, bank_card, special_health, fio
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\Media-Kit_KG_2020.pdf` | UZ-1 | volume=medium | categories=special_health, email, phone

## Sample Masked Findings
- `bank_card` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\.ipynb_checkpoints\pii_scan_results-checkpoint.csv`: **** **** **** 8121, **** **** **** 3908
- `phone` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\.ipynb_checkpoints\pii_scan_results-checkpoint.csv`: +7*** ***-**-63, +7*** ***-**-37
- `fio` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Логистика\customers.csv`: Фи***ев, Ва***ва
- `phone` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Логистика\logistics.csv`: +7*** ***-**-00, +7*** ***-**-07
- `special_health` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Логистика\logistics.csv`: медицинский
- `phone` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Логистика\sales.csv`: +7*** ***-**-19, +7*** ***-**-03
- `fio` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Логистика\stores.csv`: Ни***од
- `special_health` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Сайты\page_1.html`: здоровье
- `special_health` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Сайты\page_101.html`: здоровье
- `special_health` in `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Сайты\page_102.html`: здоровье

## Errors
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Выгрузки\Сайты\Доки\Russia.pdf`: Failed to open file 'C:\\Coding\\pytorchlabs\\ПДнDataset\\ПДнDataset\\share\\Выгрузки\\Сайты\\Доки\\Russia.pdf'.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\20120518_D212-208-10_01-04-03_TimoshenkoPE.pdf`: Failed to open file 'C:\\Coding\\pytorchlabs\\ПДнDataset\\ПДнDataset\\share\\Прочее\\20120518_D212-208-10_01-04-03_TimoshenkoPE.pdf'.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\5776_28_95fdcc53bcbe0af1e40685a74fe55ce6.pdf`: Failed to open file 'C:\\Coding\\pytorchlabs\\ПДнDataset\\ПДнDataset\\share\\Прочее\\5776_28_95fdcc53bcbe0af1e40685a74fe55ce6.pdf'.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\Problems.docx`: File is not a zip file
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\Rasporiagenie-1092-p_publications.xls`: Excel file format cannot be determined, you must specify an engine manually.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\mn1p_2016.docx`: File is not a zip file
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\podiadok-priema-bakalavr-spets-2025.pdf`: Failed to open file 'C:\\Coding\\pytorchlabs\\ПДнDataset\\ПДнDataset\\share\\Прочее\\podiadok-priema-bakalavr-spets-2025.pdf'.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\resh_minobr_10111998.pdf`: Failed to open file 'C:\\Coding\\pytorchlabs\\ПДнDataset\\ПДнDataset\\share\\Прочее\\resh_minobr_10111998.pdf'.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\resh_minobr_19082002.pdf`: Failed to open file 'C:\\Coding\\pytorchlabs\\ПДнDataset\\ПДнDataset\\share\\Прочее\\resh_minobr_19082002.pdf'.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\sved_o_d_m_2017.xls`: Excel file format cannot be determined, you must specify an engine manually.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Прочее\Ð Ð¾ÑÑÐ¾Ð²-Ð½Ð°-ÐÐ¾Ð½Ñ.pdf`: Failed to open file 'C:\\Coding\\pytorchlabs\\ПДнDataset\\ПДнDataset\\share\\Прочее\\Ð\xa0Ð¾Ñ\x81Ñ\x82Ð¾Ð²-Ð½Ð°-Ð\x94Ð¾Ð½Ñ\x83.pdf'.

## Warnings
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza00d00\50308888-8889.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza01f00\0011839665.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza04e00\2040765768.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza17e00\2031309105.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza20e00\04303523-a.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza23d00\513327776_513327782.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza27d00\2075165787.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza29e00\2501172233_2501172290.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza42d00\2050801870_1873.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza43e00\2042537535.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza44e00\2023086413.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza49e00\2501298013.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza50f00\0000269666.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza51c00\2085779941.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza54c00\80702501.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza57d00\2048755106.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza58c00\2083822795.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza61e00\00620531.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza65e00\2046440775.tif`: Image OCR skipped in fast mode.
- `C:\Coding\pytorchlabs\ПДнDataset\ПДнDataset\share\Архив сканы\a\zza70e00\92023499_92023505.tif`: Image OCR skipped in fast mode.
