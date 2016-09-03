from selenium import webdriver

browser = webdriver.Chrome()

pac_pool = 'https://nike.uwaterloo.ca/FacilityScheduling/FacilitySchedule.aspx?FacilityId=5d72208a-069d-4931-aaa6-9527346efc6f'

# open the page
browser.get(pac_pool)

# look for the element showing the date
    # this element also has class dxscAlternateDateHeader_Metropolis
elem_day = browser.find_element_by_class_name('dxscDateHeader_Metropolis')

print elem_day.get_attribute('title')
print elem_day.text

# look for the element containing all the scheduled events for the day
# need to find a way to iterate through these
elem_events = browser.find_element_by_id('ctl00_contentMain_schedulerMain_containerBlock_verticalContainerappointmentLayer')
# just contains all the event text concatenated
    # there are separate elements for the start and finish times, and description for each event, so we can do better than this
print elem_events.text

# click forward button to move to next day
    # in theory, it should be more efficient to use the week or month view,
    # but they don't actually contain all the event info for each day
elem_fwd_button = browser.find_element_by_id('ctl00_contentMain_schedulerMain_viewNavigatorBlock_ctl00_ctl11_CD')

# this may take some amount of time to complete - how can we detect this from within selenium?
    # maybe by periodically polling whether or not the element has gone stale?
    # in this case, trying to read a property, such as text, will raise a StaleElementReferenceException
elem_fwd_button.click()

# browser.quit()