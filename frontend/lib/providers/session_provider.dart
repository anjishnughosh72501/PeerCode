import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../bridge/bridge_client.dart';
import '../models/peer.dart';
import '../models/session.dart';

part 'session_provider.g.dart';

@riverpod
BridgeClient bridgeClient(BridgeClientRef ref) => const BridgeClient();

@riverpod
class SessionNotifier extends _$SessionNotifier {
  @override
  Session? build() => null;

  Future<void> startHost(String name, String filepath) async {
    final response =
        await ref.read(bridgeClientProvider).hostProject(name, filepath);
    state = Session(
      role: SessionRole.host,
      filename: response['project_name'] as String? ??
          filepath.split(RegExp(r'[\\/]')).last,
      localName: name,
      peers: <Peer>[
        Peer(name: name, color: colorFromHex('#7C84FA'), isHost: true)
      ],
      isConnected: true,
    );
  }

  Future<void> joinGuest(String name, String ip, int port) async {
    await ref
        .read(bridgeClientProvider)
        .connectToGuest(name, ip: ip, port: port);
    state = Session(
      role: SessionRole.guest,
      filename: 'Remote file',
      localName: name,
      peers: <Peer>[
        Peer(name: name, color: colorFromHex('#36D399'), isHost: false)
      ],
      isConnected: true,
    );
  }

  Future<void> disconnect() async {
    await ref.read(bridgeClientProvider).disconnect();
    state = null;
  }

  void addPeer(Peer peer) {
    final current = state;
    if (current == null) return;
    final peers = <Peer>[
      ...current.peers.where((p) => p.name != peer.name),
      peer
    ];
    state = current.copyWith(peers: peers);
  }

  void removePeer(String name) {
    final current = state;
    if (current == null) return;
    state = current.copyWith(
        peers: current.peers.where((p) => p.name != name).toList());
  }

  void setPeers(List<Peer> peers) {
    final current = state;
    if (current == null) return;
    state = current.copyWith(peers: peers);
  }

  void setFilename(String filename) {
    final current = state;
    if (current == null) return;
    state = current.copyWith(filename: filename);
  }

  void setConnected(bool connected) {
    final current = state;
    if (current == null) return;
    state = current.copyWith(isConnected: connected);
  }
}
