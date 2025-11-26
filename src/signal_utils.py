# Libraries

import numpy as np
from itertools import groupby


# Helpers

def sec_to_tp(sec, sampl_rate):
    '''
    Convert from seconds to timepoint
    
    :param sec: Float
    :param sampl_rate: Float
    :return: Int
    '''
    return int(sec * sampl_rate)
	

def trim_start(raw_signal, trim_tps=350000):
    '''
    Trim first n timepoints
    
    :param raw_signal: np.array
    :param trim_tps: Int
    :return: np.array
    '''
    # Prepend zeros so the trimmed array preserves original indexing downstream.
    return np.concatenate((np.zeros(trim_tps, dtype=float), raw_signal[trim_tps:]))
	

def get_baseline(filtered_ary, lower=150, upper=400):
    '''
    Determine baseline open pore current
    
    :param filtered_ary: np.array
    :param lower: Int
    :param upper: Int
    :return: Float or None
    '''
    consts = {'min_ary_mean': 50.0, 'min_ary_std': 10.0, 'min_subset_n_prop': 0.01}
    baseline_out = None
    
    # Channel QC
    if filtered_ary.mean() > consts['min_ary_mean'] and filtered_ary.std() > consts['min_ary_std']:
        
        # Find baseline
        # Focus on the putative open-pore range to avoid event contamination.
        signal_subset = filtered_ary[(filtered_ary > lower) & (filtered_ary < upper)]
        
        # Signal range QC
        if len(signal_subset) > len(filtered_ary) * consts['min_subset_n_prop']:
            baseline_out = np.median(signal_subset)
    
    if baseline_out is None:
        print('Failed to identify baseline Io - bad channel')
        
    return baseline_out
	
	
def merge_consecutive_bool(lst):
    '''
    Example:
        [True, True, False, False, False, True] => [(True, (0, 2)), (False, (2, 5)), (True, (5, 6))]
        
    :params condition: np.array<Bool>
    :return: List<Bool, Tup<Int, Int>>
    '''
    run_sum = 0
    out_lst = []
    count_bool = [(key, sum(1 for _ in group)) for key, group in groupby(lst)]
    for tup in count_bool:
        start = run_sum
        run_sum += tup[1]
        out_lst.append((tup[0], (start, run_sum)))
        
    # Must start and end with True state
    
    if out_lst[0][0] == False:
        out_lst = out_lst[1:]
    if out_lst[-1][0] == False:
        out_lst = out_lst[:-1]
    return out_lst


def get_tranloc_idx(ex_filt_sig, baseline_pA, baseline_dev=30, t_range=(4, 150), min_depth_range=(0.0, 0.4), strict_depth=0.6):
    '''
    Get predicted indices of translocation events
    
    :param ex_filt_sig: np.array<Float>
    :param baseline_pA: Float
    :param baseline_dev: Int
    :param t_range: Tuple
    :param depth_range: Tuple
    :return: List<Tuple>
    '''
    assert len(t_range) == 2
    assert len(min_depth_range) == 2
    min_duration = t_range[0]
    max_duration = t_range[1]
    lower_depth_thresh = min_depth_range[0] * baseline_pA
    upper_depth_thresh = min_depth_range[1] * baseline_pA
    upper_strict_depth = strict_depth * baseline_pA

    # Boolean mask marking samples that stay within the baseline envelope.
    median_band = np.array((ex_filt_sig < baseline_pA + baseline_dev) & (ex_filt_sig > baseline_pA - baseline_dev))
    merged_idx = merge_consecutive_bool(median_band)

    filtered_idx = []
    for key, idx in merged_idx:
        if key == False:
            duration = idx[1] - idx[0]
            # Filter 1: keep only candidate drops that last within the allowed time window.
            if duration >= min_duration and duration <= max_duration:
                drop_current = ex_filt_sig[idx[0]:idx[1]]
                min_current = drop_current.min()
                # Filter 2: reject segments that do not drop far enough (or drop too far).
                if min_current < upper_depth_thresh and min_current > lower_depth_thresh:
                    # Filter 3: require every point in the segment to stay below the strict Ir/Io ceiling.
                    if np.all(drop_current < upper_strict_depth):
                        filtered_idx.append(idx)
    print('{} events detected.'.format(len(filtered_idx)))
    return filtered_idx
	

# Main
	
def get_signal_pA(chann_info):
    '''
    Convert raw Nanopore signals to pA
    
    :param chann_info: <Channel_Info>
    :return: np.array
    '''
    raw_unit = chann_info.parange / chann_info.digitisation
    pa_sig = (chann_info.raw_signal + chann_info.offset) * raw_unit
    return pa_sig
	
	
def detect_events(sig_ary, **kwargs):
    '''
    Detect events from a single channel
    
    :param sig_ary: np.array<Float>
    :return: Dict
    '''
    out_dict = {'open_current': -1.0, 'event_idx': []}
    
    # 1. Trim
    trim_sig = trim_start(sig_ary)
    # Removing the initial drift keeps indices stable while discarding the high-noise warm-up region.
    
    # 2. Determine open pore baseline current
    open_pA = get_baseline(trim_sig)
    # Without a reliable baseline Io we cannot reason about Ir/Io, so bail out early if it fails.
    
    # 3. Find events
    if open_pA is not None:
        transloc_idx = get_tranloc_idx(trim_sig, open_pA, **kwargs)
        out_dict['open_current'] = open_pA
        out_dict['event_idx'] = transloc_idx
    return out_dict
