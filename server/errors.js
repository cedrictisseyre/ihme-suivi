export class InputError extends Error {
  constructor(message) {
    super(message);
    this.status = 400;
  }
}
