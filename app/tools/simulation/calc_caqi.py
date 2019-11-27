# CAQI calculations based on https://github.com/hicklin/Common-Air-Quality-Index-for-R/blob/master/caqi.R
def calc_nox_index(val):
    sub_index = 0
    if val < 100:
        sub_index = val / 2
    elif val > 200:
        sub_index = (val / 8) + 50
    else:
        sub_index = (val / 4) + 25
    return sub_index

def calc_pmx_index(val):
    sub_index = 0
    if val < 50:
        sub_index = val
    elif val > 90:
        sub_index = ((5 * val) / 18) + 50
    else:
        sub_index = ((5 * val) / 8) + 18.75
    return sub_index

def calc_co_index(val):
    sub_index = 0
    if val < 5000:
        sub_index = val / 200
    elif val > 10000:
        sub_index = (val / 400) + 50
    else:
        sub_index = (val / 100) - 25
    return sub_index

def calc_overall_caqi(si_pm, si_no, si_co):
    return max(si_pm, si_no, si_co)

def calc_indices(row):
    row['NOx'] = calc_nox_index(row['NOx'])
    row['PMx'] = calc_pmx_index(row['PMx'])
    row['CO'] = calc_co_index(row['CO'])
    row['CAQI'] = row[['NOx', 'PMx', 'CO']].max()
    return row