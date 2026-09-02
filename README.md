
# carParser.py

A simple, thread-safe serial protocol parser/writer for a car/robot
controller board.

Usage:
```py
    import carParser
    carParser.init("/dev/AMA0", 921600)

    imu = carParser.getIMU()        # [gx, gy, gz, ax, ay, az, roll, pitch, yaw]
    dist = carParser.getDIST()      # [l1, l2, l3, l4]
    adc = carParser.getADC()        # [val1, val2, val3, val4]
    btn = carParser.getButton()     # [x, y]
    col = carParser.getColor()      # [lux, r, g, b]
    obs = carParser.getObstacle()   # [val, timestamp]

    carParser.move(1, 2, 3)
    carParser.beep(1, 2)
    carParser.servo(1, 2, 3, 4)
    carParser.led(1, 2)
```

Wire format (all lines newline-terminated with '\\n'):
    $IMU,gx,gy,gz,ax,ay,az,roll,pitch,yaw
    $DIST,l1,l2,l3,l4
    $ADC,val1,val2,val3,val4
    $BUTTON,x,y
    $COLOR,lux,r,g,b
    $OBSTACLE,val

Design notes:
    - A single background thread continuously reads and parses incoming
      serial lines and updates a "latest value" cache under a lock.
    - get*() functions never touch the serial port or block; they just
      return a copy of the latest cached value. This keeps caller-side
      latency essentially zero regardless of serial baud/timing.
    - Malformed lines (bad prefix, wrong field count, non-numeric field)
      are silently dropped; the previous good value is kept.
    - All cached values start at zero-filled lists (getObstacle's
      timestamp starts at 0.0) until real data arrives.
