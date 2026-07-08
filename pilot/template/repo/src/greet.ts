export function greet(name: string): string {
  // BUG: 이름 앞뒤 공백이 제거되지 않아 "Hello,  Alice !" 처럼 출력된다
  return `Hello, ${name}!`;
}
