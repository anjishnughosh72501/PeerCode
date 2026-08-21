import 'dart:async';
import 'dart:convert';

import 'package:web_socket_channel/web_socket_channel.dart';

class BridgeConnectionException implements Exception {
  BridgeConnectionException(this.message);
  final String message;

  @override
  String toString() => message;
}

class BridgeWS {
  BridgeWS();

  final StreamController<Map<String, Object?>> _events =
      StreamController<Map<String, Object?>>.broadcast();
  WebSocketChannel? _channel;
  bool _disposed = false;
  bool _connected = false;

  Stream<Map<String, Object?>> get events => _events.stream;

  Future<void> connect() async {
    var attempt = 0;
    while (!_disposed) {
      try {
        _channel =
            WebSocketChannel.connect(Uri.parse('ws://127.0.0.1:7432/ws'));
        await _channel!.ready.timeout(const Duration(seconds: 2));
        _connected = true;
        _channel!.stream.listen(
          (Object? raw) {
            final Object? decoded = jsonDecode(raw as String);
            if (decoded is Map<String, Object?>) _events.add(decoded);
          },
          onError: (_) => _reconnect(),
          onDone: _reconnect,
        );
        return;
      } catch (_) {
        attempt++;
        if (attempt > 20) {
          throw BridgeConnectionException(
              'PeerCode: could not reach backend after 20 attempts.');
        }
        await Future<void>.delayed(
            Duration(milliseconds: (300 * attempt).clamp(300, 6000)));
      }
    }
  }

  Future<void> _reconnect() async {
    if (_disposed || !_connected) return;
    _connected = false;
    await Future<void>.delayed(const Duration(seconds: 1));
    if (!_disposed) await connect();
  }

  void dispose() {
    _disposed = true;
    _channel?.sink.close();
    _events.close();
  }
}
