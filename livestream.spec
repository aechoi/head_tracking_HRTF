# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['livestream.py'],
             pathex=['C:/Users/Alex/Anaconda3/Lib/site-packages/cv2', 'C:\\Users\\Alex\\Documents\\_projTech\\1 hrtf\\3D SOUND\\livestream'],
             binaries=[],
             datas=[('C:/Users/Alex/Anaconda3/Lib/site-packages/mediapipe/modules', 'mediapipe/modules')],
             hiddenimports=['cftime'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='livestream',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='livestream')
