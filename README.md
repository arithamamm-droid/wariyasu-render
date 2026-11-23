# wariyasu-render

「割安ナビ」(https://furusato.wariyasu-navi.com/)の SNS 用の短い動画を、GitHub Actions で書き出すためのリポジトリです。
各フォルダが1本の動画のプロジェクト(HTML とアニメーション)で、[HyperFrames](https://www.npmjs.com/package/hyperframes) で mp4 にし、Python で合成した BGM・効果音を重ねます。

- 書き出し: Actions の `render` を手動で実行(`project` にフォルダ名)。出来上がりは成果物(artifact)として置かれます。
- 秘密の値やデータは置いていません。

## 権利

- 動画の絵・文言・コード・音は割安ナビのものです。転載・再配布はご遠慮ください。
- フォント: Dela Gothic One・Noto Sans JP(どちらも SIL Open Font License 1.1。`_shared/fonts/OFL-*.txt`)。配布元: https://github.com/syakuzen/DelaGothic ・ https://github.com/google/fonts/tree/main/ofl/notosansjp
- アニメーションは GSAP を CDN から読み込みます(https://gsap.com/ のライセンス)。
