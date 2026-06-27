from fugle_provider import FugleProvider
from simulation_engine import SimulationEngine


def get_market_data(
    data_source,
    api_key,
    stock_code,
    tick,
):

    if data_source == "真實盤":

        provider = FugleProvider(api_key)

        quote = provider.get_quote(stock_code)

    else:

        engine = SimulationEngine(
            mode="normal",
            base_price=100,
        )

        quote = engine.generate(
            tick,
            300,
        )

    return quote
