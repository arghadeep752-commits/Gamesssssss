export interface StarterCategory {
  id: string;
  name: string;
  nameHi: string;
  description: string;
  sortOrder: number;
}

/**
 * The initial category set from the product brief. Admins can rename, reorder,
 * hide or delete any of these; they are created once by the
 * `seedStarterCategories` function (never overwritten).
 */
export const STARTER_CATEGORIES: readonly StarterCategory[] = [
  { id: 'shri-ram', name: 'Shri Ram', nameHi: 'श्री राम', description: 'Maryada Purushottam Shri Ram of Ayodhya.' },
  { id: 'shri-krishna', name: 'Shri Krishna', nameHi: 'श्री कृष्ण', description: 'Murlidhar Kanha, the guide of the Gita.' },
  { id: 'mahadev', name: 'Mahadev', nameHi: 'महादेव', description: 'Lord Shiva, Bholenath, the Adi Yogi of Kailash.' },
  { id: 'maa-durga', name: 'Maa Durga', nameHi: 'माँ दुर्गा', description: 'The invincible Divine Mother on her lion.' },
  { id: 'maa-kali', name: 'Maa Kali', nameHi: 'माँ काली', description: 'The fierce, protective form of the Mother.' },
  { id: 'shri-hanuman', name: 'Shri Hanuman', nameHi: 'श्री हनुमान', description: 'Sankat Mochan, the devoted servant of Shri Ram.' },
  { id: 'shri-ganesh', name: 'Shri Ganesh', nameHi: 'श्री गणेश', description: 'Vighnaharta, remover of obstacles.' },
  { id: 'maa-lakshmi', name: 'Maa Lakshmi', nameHi: 'माँ लक्ष्मी', description: 'Goddess of prosperity and grace.' },
  { id: 'maa-saraswati', name: 'Maa Saraswati', nameHi: 'माँ सरस्वती', description: 'Goddess of wisdom, music and learning.' },
  { id: 'vishnu-bhagwan', name: 'Vishnu Bhagwan', nameHi: 'विष्णु भगवान', description: 'The preserver, resting on Shesh Naag.' },
  { id: 'radha-krishna', name: 'Radha Krishna', nameHi: 'राधा कृष्ण', description: 'The eternal divine love of Radha and Krishna.' },
  { id: 'ram-darbar', name: 'Ram Darbar', nameHi: 'राम दरबार', description: 'Shri Ram with Mata Sita, Lakshman and Hanuman.' },
  { id: 'shiv-parivar', name: 'Shiv Parivar', nameHi: 'शिव परिवार', description: 'Mahadev with Maa Parvati, Ganesh and Kartikeya.' },
  { id: 'vishwaroop', name: 'Vishwaroop', nameHi: 'विश्वरूप', description: 'The cosmic form revealed at Kurukshetra.' },
  { id: 'dashavatar', name: 'Dashavatar', nameHi: 'दशावतार', description: 'The ten avatars of Shri Vishnu.' },
  { id: 'hindu-temples', name: 'Hindu Temples', nameHi: 'हिंदू मंदिर', description: 'Sacred temples, shikharas and tirthas.' },
  { id: 'sanatan-symbols', name: 'Sanatan Symbols', nameHi: 'सनातन प्रतीक', description: 'Om, Swastik, Trishul, Shankh and more.' },
  { id: 'spiritual-nature', name: 'Spiritual Nature', nameHi: 'आध्यात्मिक प्रकृति', description: 'Ganga ghats, the Himalayas and sacred landscapes.' },
  { id: 'festival-wallpapers', name: 'Festival Wallpapers', nameHi: 'त्योहार', description: 'Diwali, Navratri, Holi, Janmashtami and more.' },
  { id: 'other-deities', name: 'Other Deities', nameHi: 'अन्य देवी-देवता', description: 'More gods, goddesses and devotional collections.' },
].map((c, index) => ({ ...c, sortOrder: (index + 1) * 10 }));
