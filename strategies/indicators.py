## Store all indicators here 

def sma(data, period):
    data = data.tail(period)
    sma = data['close'].mean()
    return sma

def std_dev(data, period):
    data = data.tail(period)
    std_dev = data['close'].std()
    return std_dev

# gets avg gain and avg loss for the last 14 days
def rsi(data, period):
    data = data.tail(period+1) #get last n+1 rows
    price_diff = data['close'].diff()  # Calculate price differences

    gains = price_diff.where(price_diff > 0, 0)  # Where diff > 0, keep value, else 0
    losses = -price_diff.where(price_diff < 0, 0)  # Where diff < 0, keep abs value, else 0
    avg_gain = gains.mean()
    avg_loss = losses.mean()

    rs = avg_gain/avg_loss
    rsi = 100 - 100/(1+rs)
    return rsi

def bb(data, period, num_devs=2):
    data = data.tail(period)
    sma = data['close'].mean()
    std_dev = data['close'].std()

    upper_bb = sma + std_dev*num_devs
    middle_bb = sma
    lower_bb = sma - std_dev*num_devs

    return upper_bb, middle_bb, lower_bb

def atr(data, period):
    data = data.tail(period+1)

    tr = data['high'] - data['low']
    tr = tr.combine(data['high'] - data['close'].shift(1), max)
    tr = tr.combine(data['low'] - data['close'].shift(1), max)

    atr = tr.mean()
    # print('tr', tr)
    # print('atr', atr)
    return atr
