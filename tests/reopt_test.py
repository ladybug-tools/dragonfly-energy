# coding=utf-8
from dragonfly_energy.reopt import REoptParameter, FinancialParameter, WindParameter, \
    PVParameter, StorageParameter, GeneratorParameter


def test_reopt_parameter_init():
    """Test the initialization of REoptParameter and basic properties."""
    re_par = REoptParameter()
    str(re_par)  # test the string representation

    assert isinstance(re_par.financial_parameter, FinancialParameter)
    assert isinstance(re_par.wind_parameter, WindParameter)
    assert isinstance(re_par.pv_parameter, PVParameter)
    assert isinstance(re_par.storage_parameter, StorageParameter)
    assert isinstance(re_par.generator_parameter, GeneratorParameter)

    str(re_par.financial_parameter)
    str(re_par.wind_parameter)
    str(re_par.pv_parameter)
    str(re_par.storage_parameter)
    str(re_par.generator_parameter)

    assert re_par.financial_parameter.analysis_years == 25
    assert re_par.financial_parameter.escalation_rate == 0.023
    assert re_par.financial_parameter.tax_rate == 0.26
    assert re_par.financial_parameter.discount_rate == 0.083

    assert re_par.wind_parameter.max_kw == 0
    assert re_par.pv_parameter.max_kw == 0
    assert re_par.storage_parameter.max_kw == 0
    assert re_par.generator_parameter.max_kw == 0

    re_par_dup = re_par.duplicate()
