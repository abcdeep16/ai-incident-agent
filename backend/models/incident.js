class Incident {
  constructor({ title, description, service, severity }) {
    this.title = title;
    this.description = description;
    this.service = service;
    this.severity = severity;
  }
}

module.exports = Incident;