import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../models/peer.dart';

part 'peers_provider.g.dart';

class PeersState {
  const PeersState({required this.connected, required this.discovered});
  final List<Peer> connected;
  final List<DiscoveredHost> discovered;

  PeersState copyWith({List<Peer>? connected, List<DiscoveredHost>? discovered}) {
    return PeersState(connected: connected ?? this.connected, discovered: discovered ?? this.discovered);
  }
}

@riverpod
class PeersNotifier extends _$PeersNotifier {
  @override
  PeersState build() => const PeersState(connected: <Peer>[], discovered: <DiscoveredHost>[]);

  void setConnected(List<Peer> peers) {
    state = state.copyWith(connected: peers);
  }

  void setDiscovered(List<DiscoveredHost> hosts) {
    state = state.copyWith(discovered: hosts);
  }

  void addDiscovered(DiscoveredHost host) {
    final hosts = <DiscoveredHost>[...state.discovered.where((h) => h.ip != host.ip), host];
    state = state.copyWith(discovered: hosts);
  }

  void removeDiscovered(String ip) {
    state = state.copyWith(discovered: state.discovered.where((h) => h.ip != ip).toList());
  }
}
