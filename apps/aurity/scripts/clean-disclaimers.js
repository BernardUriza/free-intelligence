/**
 * Clean disclaimer messages from localStorage
 *
 * Run in browser console:
 * node apps/aurity/scripts/clean-disclaimers.js
 */

// Get all localStorage keys for FI chat
const chatKeys = Object.keys(localStorage).filter(key => key.startsWith('fi_chat_'));

console.log(`Found ${chatKeys.length} chat keys`);

chatKeys.forEach(key => {
  const messages = JSON.parse(localStorage.getItem(key) || '[]');

  // Filter out disclaimer messages (check content for HIPAA/protección keywords)
  const cleaned = messages.filter(msg => {
    const content = msg.content.toLowerCase();
    return !(
      content.includes('hipaa') ||
      content.includes('protección de datos') ||
      content.includes('estándares de protección') ||
      content.includes('aplicación que estás utilizando')
    );
  });

  if (cleaned.length !== messages.length) {
    console.log(`${key}: Removed ${messages.length - cleaned.length} disclaimer messages`);
    localStorage.setItem(key, JSON.stringify(cleaned));
  }
});

console.log('✅ Cleanup complete!');
