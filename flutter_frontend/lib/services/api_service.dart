import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;
import '../models/report_model.dart';

class ApiService {
  // Use http://10.0.2.2:8000 for Android emulator, http://127.0.0.1:8000 for web/desktop
  static String baseUrl = "http://127.0.0.1:8000";

  static Future<MedicalReport?> loadSampleReport(String sampleType) async {
    try {
      final res = await http.post(
        Uri.parse("$baseUrl/api/sample-report?sample_type=$sampleType&patient_name=Sarah%20Connor"),
      );
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        if (data['success'] == true && data['record'] != null) {
          return MedicalReport.fromJson(data['record']);
        }
      }
    } catch (e) {
      print("Error loading sample report: $e");
    }
    return null;
  }

  static Future<MedicalReport?> uploadReportBytes(Uint8List bytes, String filename, String patientName) async {
    try {
      var request = http.MultipartRequest("POST", Uri.parse("$baseUrl/api/analyze-report"));
      request.fields['patient_name'] = patientName;
      request.files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
        ),
      );

      var streamedResponse = await request.send();
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success'] == true && data['record'] != null) {
          return MedicalReport.fromJson(data['record']);
        }
      }
    } catch (e) {
      print("Error uploading report: $e");
    }
    return null;
  }

  static Future<MedicalReport?> getReportByToken(String token) async {
    try {
      final res = await http.get(Uri.parse("$baseUrl/api/reports/$token"));
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        return MedicalReport.fromJson(data);
      }
    } catch (e) {
      print("Error fetching report by token: $e");
    }
    return null;
  }

  static Future<List<Doctor>> getDoctors() async {
    try {
      final res = await http.get(Uri.parse("$baseUrl/api/doctors"));
      if (res.statusCode == 200) {
        final List<dynamic> list = json.decode(res.body);
        return list.map((d) => Doctor.fromJson(d)).toList();
      }
    } catch (e) {
      print("Error fetching doctors: $e");
    }
    return [];
  }

  static Future<bool> bookAppointment({
    required String patientName,
    required String patientPhone,
    required String doctorId,
    required String date,
    required String time,
    required String reason,
    String? reportToken,
  }) async {
    try {
      final res = await http.post(
        Uri.parse("$baseUrl/api/appointments"),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          "patient_name": patientName,
          "patient_phone": patientPhone,
          "doctor_id": doctorId,
          "date": date,
          "time": time,
          "reason": reason,
          "report_token": reportToken,
        }),
      );
      return res.statusCode == 200;
    } catch (e) {
      print("Error booking appointment: $e");
      return false;
    }
  }

  static Future<List<Appointment>> getAppointments({String? doctorId, String? patientName}) async {
    try {
      String url = "$baseUrl/api/appointments";
      if (doctorId != null) url += "?doctor_id=$doctorId";
      final res = await http.get(Uri.parse(url));
      if (res.statusCode == 200) {
        final List<dynamic> list = json.decode(res.body);
        return list.map((a) => Appointment.fromJson(a)).toList();
      }
    } catch (e) {
      print("Error fetching appointments: $e");
    }
    return [];
  }

  static Future<bool> addDoctorNotes(String reportId, String doctorName, String notes) async {
    try {
      final res = await http.post(
        Uri.parse("$baseUrl/api/reports/$reportId/notes"),
        headers: {"Content-Type": "application/json"},
        body: json.encode({"doctor_name": doctorName, "notes": notes}),
      );
      return res.statusCode == 200;
    } catch (e) {
      print("Error adding doctor notes: $e");
      return false;
    }
  }

  static Future<Map<String, dynamic>?> askVoiceQuery(String queryText, {String? reportId}) async {
    try {
      final res = await http.post(
        Uri.parse("$baseUrl/api/voice/query"),
        headers: {"Content-Type": "application/json"},
        body: json.encode({"query_text": queryText, "report_id": reportId}),
      );
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (e) {
      print("Error querying voice pipeline: $e");
    }
    return null;
  }

  static Future<Map<String, dynamic>?> sendChatMessage({
    required String message,
    String? reportId,
    List<Map<String, String>> history = const [],
  }) async {
    try {
      final res = await http.post(
        Uri.parse("$baseUrl/api/chat"),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          "message": message,
          "report_id": reportId,
          "history": history,
        }),
      );
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (e) {
      print("Error in chat: $e");
    }
    return null;
  }
}

