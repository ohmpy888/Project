import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Target, 
  Users, 
  Calendar,
  TrendingUp,
  Award,
  BookOpen,
  PlayCircle,
  Star,
  CheckCircle,
  Brain,
  Zap
} from 'lucide-react';

const NewsVerificationLanding = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userStats, setUserStats] = useState({
    streak: 7,
    accuracy: 85,
    totalChallenges: 42,
    lastBadge: "Truth Seeker"
  });

  const [globalStats] = useState({
    totalUsers: 15247,
    challengesToday: 1873,
    accuracyRate: 78
  });

  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const timeUntilMidnight = () => {
    const now = new Date();
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(0, 0, 0, 0);
    
    const diff = tomorrow - now;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);
    
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const features = [
    {
      icon: Brain,
      title: "AI-Powered Analysis",
      description: "โมเดล CNN + BiLSTM + Attention ที่ผ่านการเทรนแล้ว"
    },
    {
      icon: Target,
      title: "Daily Challenge",
      description: "โจทย์ใหม่ทุกวัน เพื่อสร้างนิสัยคิดวิเคราะห์"
    },
    {
      icon: Award,
      title: "Gamified Learning",
      description: "สะสม streak, ปลดล็อก badge และแข่งขันกับเพื่อน"
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-blue-50 to-purple-50">
      {/* Header */}
      <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-2 rounded-xl">
                <Shield className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">TruthCheck</h1>
                <p className="text-sm text-gray-600">ฝึกแยกข่าวจริง-ปลอม</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {!isLoggedIn ? (
                <>
                  <button 
                    onClick={() => setIsLoggedIn(true)}
                    className="text-gray-700 hover:text-blue-600 font-medium transition-colors"
                  >
                    เข้าสู่ระบบ
                  </button>
                  <button className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-2 rounded-xl hover:shadow-lg transition-all duration-300 transform hover:scale-105">
                    สมัครสมาชิก
                  </button>
                </>
              ) : (
                <div className="flex items-center space-x-3">
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">สวัสดี, User!</p>
                    <p className="text-xs text-gray-600">Streak: {userStats.streak} วัน</p>
                  </div>
                  <div className="w-10 h-10 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white font-bold">
                    U
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <div className="inline-flex items-center space-x-2 bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium">
                  <Zap className="h-4 w-4" />
                  <span>AI-Powered News Verification</span>
                </div>
                
                <h1 className="text-5xl lg:text-6xl font-bold text-gray-900 leading-tight">
                  ฝึกแยก
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600">
                    ข่าวจริง
                  </span>
                  <br />ให้เป็นนิสัย
                </h1>
                
                <p className="text-xl text-gray-600 leading-relaxed">
                  สร้างทักษะการคิดเชิงวิพากษ์ด้วย Daily Challenge ที่ขับเคลื่อนด้วย AI 
                  พร้อมฟีดแบ็กแบบเรียลไทม์และการเรียนรู้ที่ปรับตัวได้
                </p>
              </div>

              {isLoggedIn && (
                <div className="bg-white/70 backdrop-blur-sm rounded-2xl p-6 border border-gray-200/50">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">สถานะของคุณ</h3>
                    <div className="flex items-center space-x-1">
                      <Star className="h-4 w-4 text-yellow-500" />
                      <span className="text-sm text-gray-600">{userStats.lastBadge}</span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">{userStats.streak}</div>
                      <div className="text-sm text-gray-600">วันติดต่อกัน</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">{userStats.accuracy}%</div>
                      <div className="text-sm text-gray-600">ความแม่นยำ</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">{userStats.totalChallenges}</div>
                      <div className="text-sm text-gray-600">โจทย์ที่ทำ</div>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-4">
                <button className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-8 py-4 rounded-xl text-lg font-semibold hover:shadow-xl transition-all duration-300 transform hover:scale-105 flex items-center justify-center space-x-2">
                  <PlayCircle className="h-6 w-6" />
                  <span>เริ่ม Daily Challenge</span>
                </button>
                
                <button className="border-2 border-gray-300 text-gray-700 px-8 py-4 rounded-xl text-lg font-semibold hover:border-blue-600 hover:text-blue-600 transition-colors flex items-center justify-center space-x-2">
                  <BookOpen className="h-6 w-6" />
                  <span>เรียนรู้เพิ่มเติม</span>
                </button>
              </div>
            </div>

            {/* Stats Card */}
            <div className="lg:pl-12">
              <div className="bg-white/80 backdrop-blur-md rounded-3xl p-8 border border-gray-200/50 shadow-xl">
                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">Challenge วันนี้</h3>
                  <div className="inline-flex items-center space-x-2 bg-gradient-to-r from-orange-100 to-red-100 text-orange-800 px-4 py-2 rounded-full">
                    <Calendar className="h-4 w-4" />
                    <span className="font-medium">เหลือเวลา {timeUntilMidnight()}</span>
                  </div>
                </div>

                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-blue-50 rounded-xl p-4 text-center">
                      <Users className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                      <div className="text-2xl font-bold text-blue-600">{globalStats.totalUsers.toLocaleString()}</div>
                      <div className="text-sm text-gray-600">ผู้ใช้ทั้งหมด</div>
                    </div>
                    
                    <div className="bg-green-50 rounded-xl p-4 text-center">
                      <Target className="h-8 w-8 text-green-600 mx-auto mb-2" />
                      <div className="text-2xl font-bold text-green-600">{globalStats.challengesToday.toLocaleString()}</div>
                      <div className="text-sm text-gray-600">ทำวันนี้แล้ว</div>
                    </div>
                  </div>

                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-gray-700 font-medium">ความแม่นยำเฉลี่ย</span>
                      <span className="text-2xl font-bold text-purple-600">{globalStats.accuracyRate}%</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div 
                        className="bg-gradient-to-r from-purple-600 to-pink-600 h-3 rounded-full transition-all duration-1000"
                        style={{width: `${globalStats.accuracyRate}%`}}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              ทำไมต้องเลือก TruthCheck?
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              ด้วยเทคโนโลยี AI ล้ำสมัยและระบบเกมมิฟิเคชัน เพื่อให้การเรียนรู้เป็นเรื่องสนุก
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => {
              const IconComponent = feature.icon;
              return (
                <div 
                  key={index}
                  className="bg-white rounded-2xl p-8 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:scale-105 border border-gray-100"
                >
                  <div className="bg-gradient-to-r from-blue-600 to-purple-600 w-16 h-16 rounded-xl flex items-center justify-center mb-6">
                    <IconComponent className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-3">{feature.title}</h3>
                  <p className="text-gray-600 leading-relaxed">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl p-12 text-white">
            <h2 className="text-4xl font-bold mb-4">
              เริ่มต้นการเดินทางของคุณวันนี้
            </h2>
            <p className="text-xl mb-8 text-blue-100">
              เพียง 5 นาทีต่อวัน คุณจะพัฒนาทักษะการแยกแยะข่าวจริง-ปลอมได้อย่างเป็นระบบ
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="bg-white text-blue-600 px-8 py-4 rounded-xl text-lg font-semibold hover:shadow-lg transition-all duration-300 transform hover:scale-105">
                เริ่มฟรีทันที
              </button>
              <button className="border-2 border-white text-white px-8 py-4 rounded-xl text-lg font-semibold hover:bg-white hover:text-blue-600 transition-colors">
                ดูตัวอย่าง
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="col-span-2">
              <div className="flex items-center space-x-3 mb-4">
                <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-2 rounded-xl">
                  <Shield className="h-6 w-6 text-white" />
                </div>
                <span className="text-xl font-bold">TruthCheck</span>
              </div>
              <p className="text-gray-400 mb-4">
                แพลตฟอร์มฝึกแยกข่าวจริง-ปลอมด้วย AI เพื่อสร้างสังคมที่มีวิจารณญาณ
              </p>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">เมนู</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#" className="hover:text-white transition-colors">Daily Challenge</a></li>
                <li><a href="#" className="hover:text-white transition-colors">เรียนรู้</a></li>
                <li><a href="#" className="hover:text-white transition-colors">อันดับ</a></li>
                <li><a href="#" className="hover:text-white transition-colors">ประวัติ</a></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold mb-4">ติดต่อ</h4>
              <ul className="space-y-2 text-gray-400">
                <li><a href="#" className="hover:text-white transition-colors">เกี่ยวกับเรา</a></li>
                <li><a href="#" className="hover:text-white transition-colors">นโยบาย</a></li>
                <li><a href="#" className="hover:text-white transition-colors">ช่วยเหลือ</a></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
            <p>&copy; 2025 TruthCheck. สงวนลิขสิทธิ์.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default NewsVerificationLanding;