from prometheus_client import Counter, Gauge, Histogram, start_http_server

from monitor.database.events import (BlockchainStateEvent, SilicoinEvent, ConnectionsEvent, FarmingInfoEvent,
                                     HarvesterPlotsEvent, PoolStateEvent, PriceEvent, SignagePointEvent, WalletBalanceEvent)
from monitor.database.queries import get_signage_point_ts


class SilicoinExporter:
    # Wallet metrics
    total_balance_gauge = Gauge('sit_confirmed_total_mojos', 'Sum of confirmed wallet balances')
    total_farmed_gauge = Gauge('sit_farmed_total_mojos', 'Total sit farmed')

    # Full node metrics
    network_space_gauge = Gauge('sit_network_space', 'Approximation of current netspace')
    diffculty_gauge = Gauge('sit_diffculty', 'Current networks farming difficulty')
    height_gauge = Gauge('sit_peak_height', 'Block height of the current peak')
    sync_gauge = Gauge('sit_sync_status', 'Sync status of the connected full node')
    connections_gauge = Gauge('sit_connections_count', 'Count of peers that the node is currently connected to', ["type"])
    mempool_size_gauge = Gauge('sit_mempool_size', 'Current mempool size')

    # Harvester metrics
    plot_count_gauge = Gauge('sit_plot_count', 'Plot count being farmed by harvester', ["host", "type"])
    plot_size_gauge = Gauge('sit_plot_size', 'Size of plots being farmed by harvester', ["host", "type"])

    # Farmer metrics
    signage_point_counter = Counter('sit_signage_points', 'Received signage points')
    signage_point_index_gauge = Gauge('sit_signage_point_index', 'Received signage point index')
    challenges_counter = Counter('sit_block_challenges', 'Attempted block challenges')
    passed_filter_counter = Counter('sit_plots_passed_filter', 'Plots passed filter')
    proofs_found_counter = Counter('sit_proofs_found', 'Proofs found')
    lookup_time = Histogram('sit_lookup_time_seconds',
                            'Plot lookup time',
                            buckets=(.01, .05, .1, .25, .5, .75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5,
                                     3.75, 4.0, 4.25, 4.5, 4.75, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0,
                                     11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, float("inf")))

    # Pool metrics
    current_pool_points_gauge = Gauge('sit_current_pool_points',
                                      'Number of pooling points you have collected during this round', ['p2', 'url'])
    current_pool_difficulty_gauge = Gauge('sit_current_pool_difficulty', 'Difficulty of partials you are submitting',
                                          ['p2', 'url'])
    pool_points_found_since_start_gauge = Gauge('sit_pool_points_found_since_start', 'Total number of pooling points found',
                                                ['p2', 'url'])
    pool_points_acknowledged_since_start_gauge = Gauge('sit_pool_points_acknowledged_since_start',
                                                       'Total number of pooling points acknowledged', ['p2', 'url'])
    pool_points_found_24h_gauge = Gauge('sit_pool_points_found_24h', 'Number of pooling points found the last 24h',
                                        ['p2', 'url'])
    pool_points_acknowledged_24h_gauge = Gauge('sit_pool_points_acknowledged_24h',
                                               'Number of pooling points acknowledged the last 24h', ['p2', 'url'])
    num_pool_errors_24h_gauge = Gauge('sit_num_pool_errors_24h', 'Number of pool errors during the last 24 hours',
                                      ['p2', 'url'])

    # Price metrics
    price_usd_cents_gauge = Gauge('sit_price_usd_cent', 'Current sit price in USD cent')
    price_eur_cents_gauge = Gauge('sit_price_eur_cent', 'Current sit price in EUR cent')
    price_btc_satoshi_gauge = Gauge('sit_price_btc_satoshi', 'Current sit price in BTC satoshi')
    price_eth_gwei_gauge = Gauge('sit_price_eth_gwei', 'Current sit price in ETH gwei')

    last_signage_point: SignagePointEvent = None

    def __init__(self, port: int) -> None:
        start_http_server(port)

    def process_event(self, event: SilicoinEvent) -> None:
        if isinstance(event, HarvesterPlotsEvent):
            self.update_harvester_metrics(event)
        elif isinstance(event, FarmingInfoEvent):
            self.update_farmer_metrics(event)
        elif isinstance(event, ConnectionsEvent):
            self.update_connection_metrics(event)
        elif isinstance(event, BlockchainStateEvent):
            self.update_blockchain_state_metrics(event)
        elif isinstance(event, WalletBalanceEvent):
            self.update_wallet_balance_metrics(event)
        elif isinstance(event, SignagePointEvent):
            self.update_signage_point_metrics(event)
        elif isinstance(event, PoolStateEvent):
            self.update_pool_state_metrics(event)
        elif isinstance(event, PriceEvent):
            self.update_price_metrics(event)

    def update_harvester_metrics(self, event: HarvesterPlotsEvent) -> None:
        self.plot_count_gauge.labels(event.host, "OG").set(event.plot_count)
        self.plot_count_gauge.labels(event.host, "portable").set(event.portable_plot_count)
        self.plot_size_gauge.labels(event.host, "OG").set(event.plot_size)
        self.plot_size_gauge.labels(event.host, "portable").set(event.portable_plot_size)

    def update_farmer_metrics(self, event: FarmingInfoEvent):
        self.challenges_counter.inc()
        self.passed_filter_counter.inc(event.passed_filter)
        self.proofs_found_counter.inc(event.proofs)
        if self.last_signage_point is None:
            return
        if self.last_signage_point.signage_point == event.signage_point:
            signage_point_ts = self.last_signage_point.ts
        else:
            signage_point_ts = get_signage_point_ts(event.signage_point)
        lookup_time = event.ts - signage_point_ts
        self.lookup_time.observe(lookup_time.total_seconds())

    def update_connection_metrics(self, event: ConnectionsEvent) -> None:
        self.connections_gauge.labels("Full Node").set(event.full_node_count)
        self.connections_gauge.labels("Farmer").set(event.farmer_count)
        self.connections_gauge.labels("Harvester").set(event.harvester_count)

    def update_blockchain_state_metrics(self, event: BlockchainStateEvent) -> None:
        self.network_space_gauge.set(int(event.space))
        self.diffculty_gauge.set(event.diffculty)
        self.height_gauge.set(int(event.peak_height))
        self.sync_gauge.set(event.synced)
        self.mempool_size_gauge.set(event.mempool_size)

    def update_wallet_balance_metrics(self, event: WalletBalanceEvent) -> None:
        self.total_balance_gauge.set(int(event.confirmed))
        self.total_farmed_gauge.set(int(event.farmed))

    def update_signage_point_metrics(self, event: SignagePointEvent) -> None:
        self.signage_point_counter.inc()
        self.signage_point_index_gauge.set(event.signage_point_index)
        self.last_signage_point = event

    def update_pool_state_metrics(self, event: PoolStateEvent) -> None:
        p2 = event.p2_singleton_puzzle_hash
        self.current_pool_points_gauge.labels(p2, event.pool_url).set(event.current_points)
        self.current_pool_difficulty_gauge.labels(p2, event.pool_url).set(event.current_difficulty)
        self.pool_points_found_since_start_gauge.labels(p2, event.pool_url).set(event.points_found_since_start)
        self.pool_points_acknowledged_since_start_gauge.labels(p2, event.pool_url).set(event.points_acknowledged_since_start)
        self.pool_points_found_24h_gauge.labels(p2, event.pool_url).set(event.points_found_24h)
        self.pool_points_acknowledged_24h_gauge.labels(p2, event.pool_url).set(event.points_acknowledged_24h)
        self.num_pool_errors_24h_gauge.labels(p2, event.pool_url).set(event.num_pool_errors_24h)

    def update_price_metrics(self, event: PriceEvent) -> None:
        self.price_usd_cents_gauge.set(event.usd_cents)
        self.price_eur_cents_gauge.set(event.eur_cents)
        self.price_btc_satoshi_gauge.set(event.btc_satoshi)
        self.price_eth_gwei_gauge.set(event.eth_gwei)
