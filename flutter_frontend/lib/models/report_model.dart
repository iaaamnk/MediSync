class ReportParameter {
  final String name;
  final String value;
  final String referenceRange;
  final String status;
  final String explanation;

  ReportParameter({
    required this.name,
    required this.value,
    required this.referenceRange,
    required this.status,
    required this.explanation,
  });

  factory ReportParameter.fromJson(Map<String, dynamic> json) {
    return ReportParameter(
      name: json['name'] ?? '',
      value: json['value'] ?? '',
      referenceRange: json['reference_range'] ?? 'N/A',
      status: json['status'] ?? 'Normal',
      explanation: json['explanation'] ?? '',
    );
  }
}

class DoctorNote {
  final String id;
  final String doctorName;
  final String notes;
  final String createdAt;

  DoctorNote({
    required this.id,
    required this.doctorName,
    required this.notes,
    required this.createdAt,
  });

  factory DoctorNote.fromJson(Map<String, dynamic> json) {
    return DoctorNote(
      id: json['id'] ?? '',
      doctorName: json['doctor_name'] ?? '',
      notes: json['notes'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }
}

class MedicalReport {
  final String id;
  final String token;
  final String patientName;
  final String filename;
  final String createdAt;
  final String reportTitle;
  final String summaryOverview;
  final String disclaimer;
  final List<ReportParameter> parameters;
  final List<String> generalObservations;
  final List<String> questionsForDoctor;
  final List<DoctorNote> doctorNotes;

  MedicalReport({
    required this.id,
    required this.token,
    required this.patientName,
    required this.filename,
    required this.createdAt,
    required this.reportTitle,
    required this.summaryOverview,
    required this.disclaimer,
    required this.parameters,
    required this.generalObservations,
    required this.questionsForDoctor,
    required this.doctorNotes,
  });

  factory MedicalReport.fromJson(Map<String, dynamic> json) {
    final analysis = json['analysis'] ?? {};
    final paramsList = (analysis['parameters'] as List<dynamic>? ?? [])
        .map((p) => ReportParameter.fromJson(p as Map<String, dynamic>))
        .toList();

    final obsList = (analysis['general_observations'] as List<dynamic>? ?? [])
        .map((e) => e.toString())
        .toList();

    final qList = (analysis['questions_for_doctor'] as List<dynamic>? ?? [])
        .map((e) => e.toString())
        .toList();

    final notesList = (json['doctor_notes'] as List<dynamic>? ?? [])
        .map((n) => DoctorNote.fromJson(n as Map<String, dynamic>))
        .toList();

    return MedicalReport(
      id: json['id'] ?? '',
      token: json['token'] ?? '',
      patientName: json['patient_name'] ?? 'Patient',
      filename: json['filename'] ?? '',
      createdAt: json['created_at'] ?? '',
      reportTitle: analysis['report_title'] ?? 'Laboratory Report',
      summaryOverview: analysis['summary_overview'] ?? '',
      disclaimer: analysis['disclaimer'] ?? 'For educational purposes only. Does not diagnose diseases.',
      parameters: paramsList,
      generalObservations: obsList,
      questionsForDoctor: qList,
      doctorNotes: notesList,
    );
  }
}

class Doctor {
  final String id;
  final String name;
  final String specialty;
  final String qualification;
  final String hospital;
  final String avatar;

  Doctor({
    required this.id,
    required this.name,
    required this.specialty,
    required this.qualification,
    required this.hospital,
    required this.avatar,
  });

  factory Doctor.fromJson(Map<String, dynamic> json) {
    return Doctor(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      specialty: json['specialty'] ?? '',
      qualification: json['qualification'] ?? '',
      hospital: json['hospital'] ?? '',
      avatar: json['avatar'] ?? '👨‍⚕️',
    );
  }
}

class Appointment {
  final String id;
  final String patientName;
  final String patientPhone;
  final String doctorId;
  final String doctorName;
  final String doctorSpecialty;
  final String hospital;
  final String date;
  final String time;
  final String reason;
  final String? reportToken;
  final String status;

  Appointment({
    required this.id,
    required this.patientName,
    required this.patientPhone,
    required this.doctorId,
    required this.doctorName,
    required this.doctorSpecialty,
    required this.hospital,
    required this.date,
    required this.time,
    required this.reason,
    this.reportToken,
    required this.status,
  });

  factory Appointment.fromJson(Map<String, dynamic> json) {
    return Appointment(
      id: json['id'] ?? '',
      patientName: json['patient_name'] ?? '',
      patientPhone: json['patient_phone'] ?? '',
      doctorId: json['doctor_id'] ?? '',
      doctorName: json['doctor_name'] ?? '',
      doctorSpecialty: json['doctor_specialty'] ?? '',
      hospital: json['hospital'] ?? '',
      date: json['date'] ?? '',
      time: json['time'] ?? '',
      reason: json['reason'] ?? '',
      reportToken: json['report_token'],
      status: json['status'] ?? 'Confirmed',
    );
  }
}

