import machine

def deepsleep(timeout):
    # configure RTC.ALARM0 to be able to wake the device
    rtc = machine.RTC()
    rtc.irq(trigger=rtc.ALARM0, wake=machine.DEEPSLEEP)

    # set RTC.ALARM0 to fire after 10 minutes (waking the device)
    rtc.alarm(rtc.ALARM0, timeout)

    # put the device to sleep
    machine.deepsleep()
