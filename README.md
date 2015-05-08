# pyJacqQ
A Python implementation of Jacquez's Q statistics for space-time clustering of 
disease exposure in case-control studies. 

This Python module implements the Jacquez's Q method published by 
Jacquez et. al. [1][2][3]. Please refer to the papers in the references for 
more information on the statistics.

## Table of Contents
 - [Dependencies](#dependencies)
 - [Features](#features)
 - [Formatting Input Data](#formatting-input-data)
 - [CLI](#cli)
 - [API](#api)
 - [Copyright and License](#copyright-and-license)
 - [References](#references)

## Dependencies
The module requires Python 3.4 with numpy 1.8.2 and scipy 0.13.3.

## Features
This module provides several options for the statistics:
 - Focus geography option to query locations of interest for space-time 
 clustering.
 - Exposure clustering for finding clusters of cases that are only exposed to 
 the disease at cluster time (but later obtain the disease).
 - Case clustering for finding clusters of cases regardless of their disease 
 status at cluster time.
 - Testing under the assumption of equal disease risk for all individuals.
 - Testing that accounts for covariates when disease risk is not equal.
 - Ability to supply exposure information on a per-individual granularity.
 - Applying the binomial test discussed by Sloan et. al. [3] to deal with 
 multiple testing.
 - A Benjamini-Yekutieli False Discovery Rate correction for multiple 
 testing [4].
 - Results that can be saved to several normalized CSVs for the several 
 statistical sets.
 - API and CLI.
 - Preparser that finds data errors.

## Formatting Input Data
The analysis requires two CSVs: the residential histories of cases/contorls 
and their individual details. Optionaly, a third CSV could be provided for the 
focus geography. Please provide all dates in the format YYYYMMDD where YYYY is 
the year, MM is the month, and DD is the day. The columns in the CSV files can 
be in any order.

### Details File
This file is meant for information that does not change over time and includes 
the following columns:
 - ID: A unique identifier for the individual.
 - is_case: Whether or not the individual is a case.
 - DOD (optional): The date of diagnosis.
 - latency (optional): The estimated number of days the disease was present 
 but not diagnosed.
 - exposure_duration (optional): The estimated number of days an individual
  was exposed to the disease.
 - weight (optional): The probability the individual is a weight. This can be 
 the output from a logistic regression and used to account for covariates.
 
Here is an example, padded to read easier:
```
ID, is_case, DOD,      latency, weight,  exposure_duration
A,  0,       20150901, 33,      0.94437, 114
B,  1,       20151001, 95,      0.77554, 145
C,  1,       20150531, 193,     0.23128, 201
D,  0,       20151001, 68,      0.41648, 149
```

### Residential Histories File
This file should outline the location and times for all individual residences.
It should have the following columns:
 - ID: A unique identifier for the individual.
 - start_date: When the person started living at the residence.
 - end_date: The day an individual moved to a new place of residence.
 - x: The x-coordinate or longitude.
 - y: The y-coordinate or latitude.

Individual movement is given as a time-series. For example, say person A is 
at location (3, 8) from Jan 1, 2015 to Mar 3, 2015 and then moves to location 
(9, 7) until Apr 22, 2015. Person B stays at location (4, 5) from Jan 3, 2015 
until May 21, 2015. The histories csv would look like:
```
ID, start_date, end_date, x, y
A,  20150101,   20150312, 3, 8
A,  20150312,   20150422, 9, 7
B,  20150103,   20150521, 3, 8
```

### Focus Geography File (Optional)
This file is for locations of interest and has the same column headings as the 
residential histories file but applied to the point of interest.
Here is in example:
```
ID,      start_date, end_date, x,   y
Factory, 20150211,   20150601, -75, -5.4
River A, 20150112,   20150923, 3.4,  50
```

## CLI
The command line interface is straightforward. Simply supply the input files 
and locations to store the results. Pass flags to modify the options. Detailed 
help is accessible by passing a `-h` or `--help` flag. Below is an example of 
accessing help:
```
python3 jacqq.py --help
```
Here is an example using the provided simulation data set:
```
python3 jacqq.py --resident=tests/simulation_data/input_residence_histories.csv \
    --details=tests/simulation_data/input_details.csv  \
    --focus_data=tests/simulation_data/input_focus.csv \
    --out_global=global_results.csv --out_dates=date_results.csv \
    --out_local=local_results.csv --out_cases=case_results.csv \
    --out_focus=focus_results.csv --out_focus_local=focus_local_results.csv \
    --exposure --weights --shuffles=99 --alpha=0.05 \
    --correction='BINOM' --neighbors=15
```
By default the program will check for errors in the submitted data and 
write them to standard error. This can be suppressed by passing a `-N` or 
`--no_inspect` flag. More shorthands for the arguments and default values can be 
found by passing the `--help` flag.

## API
First import the module:
```python
import jacqq
details = "tests/simulation_data/input_details.csv"
histories = "tests/simulation_data/input_residential_histories.csv"
focus = "tests/simulation_data/input_focus.csv"
```
At this point you may elect to use the data preparser to check for errors 
given the parameters you plan to use:
```python
errors = check_data_dirty(details, histories, focus, exposure=False, weights=False):
```
This returns a list of errors present in the data that need correction, for 
example, missing attributes or wrong data types. Next intantiate a `QStatsStudy` 
object with the location of the input files:
```python
study = jacqq.QStatsStudy(details, histories, focus)
```
Then, simply call its `run_analysis` method with the desired options. 
This will return a `QStudyResults` object with person and time axes that can 
be easily queried
```python
results = study.run_analysis(k=5, use_exposure=True, use_weights=True, correction="BINOM")
```
Below are some examples.

Get one of the options used during analysis:
```python
>>> results.number_permutation_shuffles
    99
>>> results.adjusted_alpha
    0.05
```
Get global Q as (statistic case-years, p-value, significance):
```python
>>> results.Q_case_years
    (279.1835616438356, 0.01, 1)
```
Get the Qf statistic normalized by the number of cases:
```python
>>> results.normalized_Qf_case_years
    1.3102739726027397
```    
Get the Qt statistic for the slice at January 3rd, 2015:
```python
>>> results.time_slices[20150103].stat
    (46, 0.01, 1)
```
Get a list of only significant case points at that date:
```python
>>> results.time_slices[20150103].sig_points
    OrderedDict([('JG',
        <jacqq.QStudyPointResult object at 0x7f276e880d68>), ... ])
```
Get the local Q_it statistic for case 'JQ' on Jan. 3rd 2015:
```python
>>> results.time_slices[20150103].points['JQ'].stat
    (3, 0.02, 1)
>>> results.cases['JQ'].points[20150103].stat
    (3, 0.02, 1)
```
Find the x, y location of case 'JG' on Jan. 2nd, 2015:
```python
>>> results.cases['JG'].points[20150102].loc
    (73.0, 124.0)
```
Get the focus results in tabular/tuple form:
```python
>>> results.get_tabular_focus_data():
    (['id', 'Qif_case_years', 'pval', 'sig'],
        [['Away From Sources', 0.0, 1.0, 0],
        ['Large Constant', 2.052054794520548, 0.01, 1],
        ['Medium Linear', 1.8712328767123287, 0.01, 1],
        ['Small Constant', 1.3178082191780822, 0.27, 0]])
```
Get the binomal test results for dates as 
(number significant statistics, p-value, significance):
```python
>>> results.binom.dates
    (177, 1.1102230246251565e-16, 1)
```
Write the results to files:
```python
>>> results.write_to_files('global.csv', 'cases.csv', 'dates.csv',
        'local_cases.csv', 'focus_results.csv', 'focus_local.csv')
```
        
More info and examples can be obtained by using the Python `help()` function 
on module objects/classes.

## Copyright and License
Copyright Saman Jirjies, 2015. This work is available under the GPLv3. Please 
read LICENSE for more info.

## References
[1] Jacquez G, Kaufmann A, Meliker J, Goovaerts P, AvRuskin G, Nriagu J. 
Global, local and focused geographic clustering for case-control data with 
residential histories. Environmental Health: A Global Access Science Source 
2005;4(1):4. [http://www.ncbi.nlm.nih.gov/pubmed/15784151]

[2] Jacquez G, Meliker J, AvRuskin G, Goovaerts P, Kaufmann A, Wilson M, et al. 
Case-control geographic clustering for residential histories accounting for 
risk factors and covariates. International Journal of Health Geographics 
2006;5(1):32. [http://www.ncbi.nlm.nih.gov/pmc/articles/PMC1559595/]

[3] Sloan CD, Jacquez GM, Gallagher CM, Ward MH, Raaschou-Nielsen O, 
Nordsborg RB, et al. Performance of cancer cluster Q-statistics for 
case-control residential histories. Spat Spatiotemporal Epidemiol 2012 
Dec;3(4):297-310. [http://www.ncbi.nlm.nih.gov/pubmed/23149326]

[4] Benjamini Y, Yekutieli D. The Control of the False Discovery Rate in 
Multiple Testing under Dependency. The Annals of Statistics 
2001 Aug.;29(4):1165-1188.
