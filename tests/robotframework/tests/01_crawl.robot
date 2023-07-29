| *Settings* |
| Library | SeleniumLibrary
| Resource | common.robot

| *Test Cases* |
| Admin UI access
|  | Capture Element Screenshot | id=user_menu_button | user_menu_button.png
|  | Capture Element Screenshot | id=conf_menu_button | conf_menu_button.png
|  | Click Element | id=conf_menu_button
|  | Click Link | Administration
|  | Capture Page Screenshot | admin_ui.png

| Crawl a new URL
|  | Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_url
|  | Input Text | id=id_url | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Wait Until Page Contains | Create a new policy
|  | Capture Page Screenshot | crawl_new_url.png
|  | Click Element | xpath=//input[@value='Confirm']
|  | Wait Until Page Contains | Crawl status
|  | ${loc}= | Get Location
|  | Should Be Equal | ${loc} | http://127.0.0.1/admin/se/document/crawl_status/
|  | Page Should Not Contain | No crawlers running.
|  | Page Should Not Contain | exited
|  | Wait Until Page Contains | 4 documents to be recrawled | 2min
|  | Page Should Contain | idle
|  | Reload Page
|  | Wait Until Page Contains | Crawl status
|  | Scroll To Bottom
|  | Capture Page Screenshot | crawl_status.png

| Crawl policies
|  | Go To | http://127.0.0.1/admin/se/crawlpolicy/
|  | Wait Until Element Is Visible | id=result_list
|  | Capture Page Screenshot | crawl_policy_list.png
|  | Click Element | xpath=//table[@id='result_list']//a[.='.*']
|  | Scroll To Elem | //fieldset[1]
|  | Capture Page Screenshot | crawl_policy_decision_no_hilight.png
|  | Hilight | //fieldset[1]
|  | Capture Page Screenshot | crawl_policy_decision.png

|  | Reload Page
|  | Hilight | //h2[.='Browser']/..
|  | Scroll To Elem | //h2[.='Browser']/..
|  | Capture Page Screenshot | crawl_policy_browser.png

|  | Reload Page
|  | Hilight | //h2[.='HTML snapshot']/..
|  | Scroll To Elem | //h2[.='HTML snapshot']/..
|  | Capture Page Screenshot | crawl_policy_html_snapshot.png

|  | Reload Page
|  | Hilight | //h2[.='Updates']/..
|  | Scroll To Elem | //h2[.='Updates']/..
|  | Capture Page Screenshot | crawl_policy_updates.png

|  | Reload Page
|  | Execute Javascript | auth_fields = document.getElementById('authfield_set-group'); document.getElementsByTagName('fieldset')[3].append(auth_fields)
|  | Hilight | //h2[.='Authentication']/..
|  | Scroll To Elem | //h2[.='Authentication']/..
|  | Capture Page Screenshot | crawl_policy_auth.png

| Crawl on depth
|  | Reload Page
|  | Select From List By Label | id=id_condition | Depending on depth
|  | Capture Element Screenshot | //fieldset[1] | policy_on_depth.png
|  | Click Element | xpath=//input[@value="Save"]
|  | Go To | http://127.0.0.1/admin/se/document/queue/
|  | Wait Until Element Is Visible | id=id_url
|  | Input Text | id=id_url | http://127.0.0.1/screenshots/website/index.html
|  | Click Element | xpath=//input[@value='Check and queue']
|  | Hilight | id=id_crawl_depth
|  | Capture Page Screenshot | crawl_on_depth_add.png

|  | Go To | http://127.0.0.1/admin/se/crawlpolicy/add/
|  | Wait Until Element Is Visible | id=id_url_regex
|  | Input Text | id=id_url_regex | https://en.wikipedia.org/.*
|  | Input Text | id=id_crawl_depth | 2
|  | Capture Element Screenshot | //fieldset[1] | policy_all.png

| Documents
|  | Go To | http://127.0.0.1/admin/se/document/
|  | Wait Until Element Is Visible | id=result_list
|  | Capture Page Screenshot | documents_list.png
|  | ${doc_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${doc_count} | 4

| Domain
|  | Go To | http://127.0.0.1/admin/se/domainsetting/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Click Link | 127.0.0.1
|  | Capture Page Screenshot | domain_setting.png

| Cookies
|  | Run Keyword And Ignore Error | Run Command | ${SOSSE_ADMIN} | loaddata | ${CURDIR}/../cookies.json | shell=True
|  | Go To | http://127.0.0.1/admin/se/cookie/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 3
|  | Capture Page Screenshot | cookies_list.png

| Excluded URLs
|  | Go To | http://127.0.0.1/admin/se/excludedurl/add/
|  | Wait Until Element Is Visible | id=footer
|  | Capture Page Screenshot | excluded_url.png

| Search Engine
|  | Go To | http://127.0.0.1/admin/se/searchengine/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Not Be Equal As Numbers | ${dom_count} | 0
|  | Wait Until Element Is Visible | id=footer
|  | Capture Page Screenshot | search_engines_list.png
|  | Click Link | Brave
|  | Wait Until Page Contains | Long name
|  | Capture Page Screenshot | search_engine.png

| Authentication
|  | Go To | http://127.0.0.1/admin/auth/user/
|  | Wait Until Element Is Visible | id=result_list
|  | ${dom_count}= | Get Element Count | xpath=//table[@id='result_list']/tbody/tr
|  | Should Be Equal As Numbers | ${dom_count} | 1
|  | Click Link | admin
|  | Wait Until Page Contains | Important dates
|  | Capture Page Screenshot | user_management.png
