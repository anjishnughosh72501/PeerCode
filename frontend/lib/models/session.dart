import 'peer.dart';

enum SessionRole { host, guest }

class Session {
  const Session({
    required this.role,
    required this.filename,
    required this.localName,
    required this.peers,
    required this.isConnected,
  });

  final SessionRole role;
  final String filename;
  final String localName;
  final List<Peer> peers;
  final bool isConnected;

  Session copyWith({
    SessionRole? role,
    String? filename,
    String? localName,
    List<Peer>? peers,
    bool? isConnected,
  }) {
    return Session(
      role: role ?? this.role,
      filename: filename ?? this.filename,
      localName: localName ?? this.localName,
      peers: peers ?? this.peers,
      isConnected: isConnected ?? this.isConnected,
    );
  }
}
