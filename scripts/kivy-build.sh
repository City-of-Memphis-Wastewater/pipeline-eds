# Initialize buildozer.spec config file
buildozer init --specfile ./packaging/kivy/buildozer.spec 

# Build Android APK (Debug)
buildozer --specfile ./packaging/kivy/buildozer.spec app.source.dir=./src/frontend_kivy/ buildozer.bin_dir=./dist/kivy/ buildozer.build_dir=/build/kivy/ android debug

# Build Android App Bundle (Release for Play Store)
buildozer android release

# Deploy directly to connected Android device via ADB
buildozer android debug deploy run
