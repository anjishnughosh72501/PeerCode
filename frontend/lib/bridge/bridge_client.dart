import 'dart:convert';

import 'package:http/http.dart' as http;

const String kBridgeBase = 'http://127.0.0.1:7432';

class BridgeException implements Exception {
  BridgeException(this.message);
  final String message;
  @override
  String toString() => message;
}

class BridgeClient {
  const BridgeClient();

  Future<Map<String, Object?>> hostProject(String name, String projectPath) {
    return _post('/host', <String, Object?>{'name': name, 'filepath': projectPath});
  }

  Future<Map<String, Object?>> connectToGuest(String name, {String? code, String? ip, int? port}) {
    return _post('/guest/connect', <String, Object?>{
      'name': name,
      if (code != null) 'code': code,
      if (ip != null) 'host_ip': ip,
      if (port != null) 'host_port': port,
    });
  }

  Future<List<Map<String, Object?>>> getProjectTree() async {
    final res = await _post('/project/tree', <String, Object?>{});
    final tree = res['tree'] as List<Object?>? ?? <Object?>[];
    return tree.cast<Map<String, Object?>>();
  }

  Future<Map<String, Object?>> readFile(String path) async {
    return _post('/file/read', <String, Object?>{'path': path});
  }

  Future<Map<String, Object?>> saveFile(String path, String content, int version) async {
    return _post('/file/write', <String, Object?>{'path': path, 'content': content, 'version': version});
  }

  Future<void> createNode(String path, bool isDir) async {
    await _post('/file/create', <String, Object?>{'path': path, 'is_dir': isDir});
  }

  Future<void> renameNode(String path, String newName) async {
    await _post('/file/rename', <String, Object?>{'path': path, 'new_name': newName});
  }

  Future<void> deleteNode(String path) async {
    await _post('/file/delete', <String, Object?>{'path': path});
  }

  Future<void> sendCursor(String path, int line, int col, String color) async {
    await _post('/cursor', <String, Object?>{'path': path, 'line': line, 'col': col, 'color': color});
  }

  Future<void> disconnect() async {
    await _post('/disconnect', <String, Object?>{});
  }

  Future<List<Map<String, Object?>>> getPeers() async {
    final uri = Uri.parse('$kBridgeBase/peers');
    final response = await http.get(uri);
    final json = _decode(response);
    final connected = json['connected'] as List<Object?>? ?? <Object?>[];
    return connected.cast<Map<String, Object?>>();
  }

  Future<Map<String, Object?>> _post(String path, Map<String, Object?> body) async {
    final response = await http.post(
      Uri.parse('$kBridgeBase$path'),
      headers: const <String, String>{'content-type': 'application/json'},
      body: jsonEncode(body),
    );
    return _decode(response);
  }

  Map<String, Object?> _decode(http.Response response) {
    final Object? decoded = response.body.isEmpty ? <String, Object?>{} : jsonDecode(response.body);
    final json = decoded is Map<String, Object?> ? decoded : <String, Object?>{};
    if (response.statusCode != 200) {
      throw BridgeException(json['message'] as String? ?? 'Bridge request failed');
    }
    return json;
  }
}
