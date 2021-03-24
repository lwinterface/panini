for file in *
do
  [[ $file = test* ]] && pytest "$file" -p no:warnings
done